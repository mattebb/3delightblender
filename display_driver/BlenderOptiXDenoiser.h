#ifndef _H_BlenderOptixDenoise
#define _H_BlenderOptixDenoise
/*
** Copyright (c) 2018-2021 PIXAR.  All rights reserved.  This program or
** documentation contains proprietary confidential information and trade
** secrets of PIXAR.  Reverse engineering of object code is prohibited.
** Use of copyright notice is precautionary and does not imply
** publication.
**
**                      RESTRICTED RIGHTS NOTICE
**
** Use, duplication, or disclosure by the Government is subject to the
** following restrictions:  For civilian agencies, subparagraphs (a) through
** (d) of the Commercial Computer Software--Restricted Rights clause at
** 52.227-19 of the FAR; and, for units of the Department of Defense, DoD
** Supplement to the FAR, clause 52.227-7013 (c)(1)(ii), Rights in
** Technical Data and Computer Software.
**
** Pixar Animation Studios
** 1200 Park Ave
** Emeryville, CA  94608
*/

/*-------------------------------------------------------------------*/

#include <string>
#include <optix.h>
#include <iostream> // debugging

#include <cuda_runtime.h>
#include <optix_function_table_definition.h>
#include <optix_stubs.h>

class BlenderOptiXDenoiser
{
public:

    BlenderOptiXDenoiser();
    ~BlenderOptiXDenoiser();

    /// \brief takes a noisy packed buffer of floats, either RGB or RGBA
    /// and returns an internally allocated denoised version.
    ///
    /// \param src a pointer to the float pixels
    /// \param width the horizontal count of pixels
    /// \param height the vertical count of pixels
    /// \param ply either 3 (RGB) or 4 (RGBA) 
    ///
    /// \returns true if there was an error
    bool
    DenoiseBuffer(const void* src, int width, int height, int ply,
                    const void*& result);

    /// \brief if DenoiseBuffer or UnmapResult return error then this can be
    /// be used to get the last error.
    std::string
    GetLastError(void) { return m_lastError; }

    /// \brief The denoiser process might need to allocate temporary resources.
    /// This routine will release these resources and should be called after 
    /// copying out the result pixels from DenoiseBuffer to a permanent
    /// location
    ///
    /// \returns true if there was an error.
    bool
    UnmapResult(void);

private:

    /// \brief Allocate memory for denoising based in input image. This
    /// includes:
    ///     cuda memory for denoiser state
    ///     cuda memory for denoiser scratch
    ///     cuda and host memory for input and pixel buffers
    /// allocation is skipped if we have a buffer of the correct size from
    /// the last invocation.
    ///
    /// \param width horizontal size in pixels of input (and output)
    /// \param height vertical size in pixels of input (and output)
    /// \returns true if there was an error.
    bool
    allocate(unsigned int width, unsigned int height, int ply);

    /// \Brief allocate enough space for packed float image. Only reallocate
    /// if the image needs to be bigger
    /// \param width horizontal size in pixels of input (and output)
    /// \param height vertical size in pixels of input (and output)
    /// \param ply of the input color image (3 or 4)
    /// \param result the image to allocate or reallocate
    /// \returns true if there was an error.

    bool
    allocateFloatDeviceImage(unsigned int width, unsigned int height,
            unsigned int ply, OptixImage2D& result);

    /// \brief Allocate memory for denoising based in input image. This
    /// includes:
    ///     cuda memory for input pixels buffers
    ///     cuda memory for output pixel buffer
    ///     host memory for output pixel buffer
    /// allocation is skipped if we have a buffer of the correct size from
    /// the last invocation.
    ///
    /// \param width horizontal size in pixels of input (and output)
    /// \param height vertical size in pixels of input (and output)
    /// \param ply of the input color image (3 or 4)
    /// \returns true if there was an error.
    bool
    allocatePixelBuffers(unsigned int width, int unsigned height, int ply);

    /// \brief download denoise result pixels to the assumed to be allocated
    /// host buffer.
    ///
    /// \returns true if an error occured
    bool
    download(void);

    /// \brief Create if necessary the denoiser object required before
    /// calling any other routine.
    ///
    /// \param hasAlpha true if the color image has alpha channel
    /// \param useAlbebo true if subsequent denoising will use albedo
    /// \param useNormal can be true if and only if useAlbedo was true.
    ///
    /// \returns true if there was an error. 
    bool
    getDenoiser(bool hasAlpha, bool useAlbebo = false, bool useNormals = false);

    /// \brief Makes sure optix is loaded and creates the OptiX context
    ///
    /// \returns true if there was an error.
    bool
    initializeOptix(void);

    /// \brief Assumes input buffers have been allocated, transfer the pixels
    /// to the gpu
    ///
    /// \param color the color pixels in a packed buffer rgb or rgba
    /// \param albedo option albedo pixels (rgb)
    /// \param normals option normal valyes (xyz)
    /// \returns true if there was an error
    bool
    upload(const void* color, const void* albedo, const void* normals);


private:

    OptixDeviceContext m_context;

    // A float value required for the denoise process that OptiX
    // calculates for us from the inputs.
    CUdeviceptr m_intensity;

    OptixDenoiserOptions m_dnOptions;
    OptixDenoiser        m_denoiser;

    size_t          m_stateSize;
    CUdeviceptr     m_state;

    size_t          m_scratchSize;
    CUdeviceptr     m_scratch;
    
    unsigned int    m_numInputs;
    OptixImage2D    m_color;
    OptixImage2D    m_albedo;
    OptixImage2D    m_normals;

    OptixImage2D    m_output;

    float*          m_outHostBuffer;
    size_t          m_outHostBufferSize;
    

    std::string m_lastError;
};


BlenderOptiXDenoiser::BlenderOptiXDenoiser()
{
    m_context = nullptr;
    m_denoiser = nullptr;

    m_stateSize = 0;
    m_state = 0;

    m_scratchSize = 0;
    m_scratch = 0;

    m_color = { (CUdeviceptr)0, 0, 0, 0, 0,OPTIX_PIXEL_FORMAT_FLOAT3 };
    m_albedo = { (CUdeviceptr)0, 0, 0, 0, 0,OPTIX_PIXEL_FORMAT_FLOAT3 };
    m_normals = { (CUdeviceptr)0, 0, 0, 0, 0,OPTIX_PIXEL_FORMAT_FLOAT3 };
    m_output = { (CUdeviceptr)0, 0, 0, 0, 0,OPTIX_PIXEL_FORMAT_FLOAT3 };

    m_outHostBuffer = (float*)0;
    m_outHostBufferSize = 0;
}

BlenderOptiXDenoiser::~BlenderOptiXDenoiser()
{
}

bool
BlenderOptiXDenoiser::DenoiseBuffer(const void* src, int width, int height, int ply, const void*& result)
{
    m_lastError.clear();

    bool hasAlpha;
    if (ply == 3)
    {
        hasAlpha = false;
    }
    else if (ply == 4)
    {
        hasAlpha = true;
    }
    else
    {
        m_lastError = "Unsupported ply, must be 3 or 4";
        return true;
    }

    bool hasAlbedo = false;
    bool hasNormals = false;
    if (hasNormals)
    {
        m_numInputs = 3;
    }
    else if (hasAlbedo)
    {
        m_numInputs = 2;
    }
    else
    {
        m_numInputs = 1;
    }

    // don't support albedo or albedo_normal
    if (getDenoiser(hasAlpha, hasAlbedo, hasNormals))
    {
        return true;
    }

    if (allocate(width, height, ply))
    {
        return true;
    }

    if (upload((float*)src, (float*)0, (float*)0))
    {
        return true;
    }

    OptixResult rt;

    rt = optixDenoiserComputeIntensity(
        m_denoiser,
        (CUstream)0,
        &m_color,
        m_intensity,
        m_scratch, m_scratchSize);

    if (rt != OPTIX_SUCCESS)
    {
        m_lastError = "Optix failed computing intensity for denoise";
        return true;
    }

    OptixDenoiserParams params;
    params.blendFactor = 0.0f; // 1.0 == noisy image
    params.denoiseAlpha = 0;
    params.hdrIntensity = m_intensity;

    unsigned int inputOffsetX = 0;
    unsigned int inputOffsetY = 0;

    rt = optixDenoiserInvoke(m_denoiser, (CUstream)0,
        &params,
        m_state, m_stateSize,
        &m_color, m_numInputs,
        inputOffsetX, inputOffsetY,
        &m_output,
        m_scratch, m_scratchSize);
    if (rt != OPTIX_SUCCESS)
    {
        m_lastError = "Invoking denoiser failed";
        return true;
    }

    if (download())
    {
        return true;
    }

    result = (void*)m_outHostBuffer;

    return false;
}


bool
BlenderOptiXDenoiser::UnmapResult(void)
{
}
    
/// \brief OptiX logging callback
static void
optixMessageLogger(unsigned int level, const char *tag, const char *message, void *cbdata)
{
    (void)cbdata;
    const char* messageLevel;
    switch (level) {
    case 4:
        //fprintf(stderr, "d_blender: Optix [STATUS] %s %s\n", tag, message);
        break;
    case 3:
        fprintf(stderr, "d_blender: Optix [HINT] %s %s\n", tag, message);
        break;
    case 2:
        fprintf(stderr, "d_blender: Optix %s %s\n", tag, message);
        break;
    case 1:
        fprintf(stderr, "d_blender: Optix [FATAL] %s %s\n", tag, message);
            break;
    default:
        fprintf(stderr, "d_blender: Optix [UNKNOWN] %s %s\n", tag, message);
        break;
    }
}

/// \brief Return the min nvidia driver required as per the OptiX7
/// download page
static const char*
minNvidiaDriver(void)
{
#if defined(LINUX)
    return "435.12";
#else
    return "435.80"; // win32
#endif
}

bool
BlenderOptiXDenoiser::initializeOptix(void)
{
    if (m_context)
    {
        return false;
    }

    cudaError_t cudaErr = cudaMalloc((void**)&m_intensity, sizeof(float));
    if (cudaErr != cudaSuccess)
    {
        m_lastError = "No CUDA available";
        return true;
    }

    // this will find the optix shared library, load that and intialize
    // the function point table.
    OptixResult rt = optixInit();
    if (rt != OPTIX_SUCCESS)
    {
        switch (rt)
        {
        case OPTIX_ERROR_LIBRARY_NOT_FOUND:
            // no .so or .dll could be found
            m_lastError = "No NVidia (OptiX) driver was found.";
            break;
        case OPTIX_ERROR_ENTRY_SYMBOL_NOT_FOUND:
            // the optixQueryFunctionTable entry point not found
            m_lastError = "The version of OptiX found was "
            "too old for denoising.";

            break;
        default:
            // optixQueryFunctionTable failed for some reason
            m_lastError = "Optix failed to initialize for denoising.";
            break;
        }
        m_lastError += " The required driver version is ";
        m_lastError += minNvidiaDriver();
        m_lastError += " or newer";

        return true;
    }

    OptixDeviceContextOptions optix_options;
    optix_options.logCallbackFunction = optixMessageLogger;
    optix_options.logCallbackData = (void*)this;
    optix_options.logCallbackLevel = 4; // Status = 4, Hints = 3, Error = 2, Fat

    rt = optixDeviceContextCreate((CUcontext)0, &optix_options, &m_context);
    if (rt != OPTIX_SUCCESS)
    {
        return true;
    }

    return false;
}

bool
BlenderOptiXDenoiser::getDenoiser(bool hasAlpha, bool useAlbedo, bool useNormals)
{
    if (initializeOptix())
    {
        return true;
    }

    OptixDenoiserInputKind kind;
    if (!useAlbedo && !useNormals)
    { 
        kind = OPTIX_DENOISER_INPUT_RGB;
    }
    else if (useAlbedo && !useNormals)
    {
        kind = OPTIX_DENOISER_INPUT_RGB_ALBEDO;
    }
    else if (useAlbedo && useNormals)
    {
        kind = OPTIX_DENOISER_INPUT_RGB_ALBEDO;
    }
    else
    {
        m_lastError = "Cannot use normals without albedo";
        return true;
    }

    OptixPixelFormat format;
    if (hasAlpha)
    {
        format = OPTIX_PIXEL_FORMAT_FLOAT4;
    }
    else
    {
        format = OPTIX_PIXEL_FORMAT_FLOAT3;
    }

    OptixResult rt;
    if (m_denoiser)
    {
        if ((m_dnOptions.inputKind != kind) || 
            (m_dnOptions.pixelFormat != format))
        {
            // won't work for this new mode
            rt = optixDenoiserDestroy(m_denoiser);
            m_denoiser = nullptr;
            if (rt != OPTIX_SUCCESS)
            {
                m_lastError = "Failed to delete denoiser";
                return true;
            }
        }
        else
        {
            // reuse the existing denoise object.
            return false;
        }
    }

    // Make a new denoiser object.

    m_dnOptions.inputKind = kind;
    m_dnOptions.pixelFormat = format;

    rt = optixDenoiserCreate(m_context, &m_dnOptions, &m_denoiser);
    if (rt != OPTIX_SUCCESS)
    {
        return true;
    }

    rt = optixDenoiserSetModel(m_denoiser,
            OPTIX_DENOISER_MODEL_KIND_HDR, // LDR for png's etc
            (void*)0, // use nvida's training set
            0 );        // not a user training set so no size.

    if (rt != OPTIX_SUCCESS)
    {
        return true;
    }
 
    return false;
}

bool
BlenderOptiXDenoiser::allocate(unsigned int width, unsigned int height, int ply)
{
    OptixResult rt;
    OptixDenoiserSizes denoiserSizes;

    rt = optixDenoiserComputeMemoryResources(
            m_denoiser,
            (unsigned int) width,
            (unsigned int) height,
            &denoiserSizes);
    if (rt != OPTIX_SUCCESS)
    {
        return true;
    }

    cudaError_t cudaErr;
    // allocate only if we need more
    if (denoiserSizes.stateSizeInBytes > m_stateSize)
    {
        cudaErr = cudaFree((void*)m_state);
    
        if (cudaErr != cudaSuccess)
        {
            return true;
        }
        m_stateSize = 0;
        m_state = 0;
        cudaErr = cudaMalloc((void**)&m_state, denoiserSizes.stateSizeInBytes);
        if (cudaErr != cudaSuccess)
        {
            m_stateSize = 0;
            return true;
        }
        m_stateSize = denoiserSizes.stateSizeInBytes;
    }

    if (denoiserSizes.recommendedScratchSizeInBytes > m_scratchSize)
    {
        cudaErr = cudaFree((void*)m_scratch);
        if (cudaErr != cudaSuccess)
        {
            return true;
        }
        m_scratchSize = 0;
        m_scratch = 0;
        cudaErr = cudaMalloc((void**)&m_scratch,
                            denoiserSizes.recommendedScratchSizeInBytes);
        if (cudaErr != cudaSuccess)
        {
            cudaErr = cudaMalloc((void**)&m_scratch,
                                denoiserSizes.minimumScratchSizeInBytes);
            if (cudaErr != cudaSuccess)
            {
                return true;
            }
            m_scratchSize = denoiserSizes.minimumScratchSizeInBytes;
        }
        else
        {
            m_scratchSize = denoiserSizes.recommendedScratchSizeInBytes;
        }
    }

    rt = optixDenoiserSetup(
            m_denoiser,
            (CUstream)0, // default stream
            width,
            height,
            m_state,
            m_stateSize,
            m_scratch,
            m_scratchSize);

    if (rt != OPTIX_SUCCESS)
    {
        return true;
    }

    if (allocatePixelBuffers(width, height, ply))
    {
        return true;
    }

    return false;
}

bool BlenderOptiXDenoiser::allocateFloatDeviceImage(unsigned int width, 
        unsigned int height, unsigned int ply, OptixImage2D & result)
{
    // samples are all packed tightly on both cpu and gpu
    size_t pixelStrideInBytes = sizeof(float) * ply;
    size_t rowStrideInBytes = pixelStrideInBytes * width;

    size_t bufSize = rowStrideInBytes * height;
    size_t oldSize = result.pixelStrideInBytes * result.height;

    if (ply == 3)
    {
        result.format = OPTIX_PIXEL_FORMAT_FLOAT3;
    }
    else
    {
        result.format = OPTIX_PIXEL_FORMAT_FLOAT4;
    }

    result.width = width;
    result.height = height;
    result.pixelStrideInBytes = pixelStrideInBytes;
    result.rowStrideInBytes = rowStrideInBytes;

    if (oldSize > bufSize)
    {
        // already have enough bytes
        return true;
    }

    cudaError_t cudaErr;
    cudaErr = cudaFree((void*)result.data);
    if (cudaErr != cudaSuccess)
    {
        m_lastError = "Failed allocaticing memory in cudaFree";
        return true;
    }

    cudaErr = cudaMalloc((void**)&result.data, bufSize);
    if (cudaErr != cudaSuccess)
    {
        m_lastError = "Failed allocating cuda image memory";
        return true;
    }

    return false;
}

bool BlenderOptiXDenoiser::allocatePixelBuffers(unsigned int width, unsigned int height, int ply)
{
    // output gpu buffer
    if (allocateFloatDeviceImage(width, height, ply, m_output))
    {
        return true;
    }

    // output host side buffer
    size_t bufSize = m_output.rowStrideInBytes * m_output.height;
    if (m_outHostBufferSize < bufSize)
    {
        if (m_outHostBuffer)
        {
            free((void*)m_outHostBuffer);
        }
        m_outHostBuffer = (float*)malloc(bufSize);
        if (!m_outHostBuffer)
        {
            m_outHostBufferSize = 0;
            m_lastError = "malloc failed in allocatePixelBuffers";
            return true;
        }
        m_outHostBufferSize = bufSize;
    }

    // now make input gpu images
    if (allocateFloatDeviceImage(width, height, ply, m_color))
    {
        return true;
    }

    if (m_dnOptions.inputKind == OPTIX_DENOISER_INPUT_RGB)
    {
        return false;
    }

    if (allocateFloatDeviceImage(width, height, 3, m_albedo))
    {
        return true;
    }

    if (m_dnOptions.inputKind == OPTIX_DENOISER_INPUT_RGB_ALBEDO)
    {
        return false;
    }

    if (allocateFloatDeviceImage(width, height, 3, m_normals))
    {
        return true;
    }

    return false;
}


bool 
BlenderOptiXDenoiser::upload(const void* color, const void* albedo, const void* normals)
{
    size_t bufSize;
    cudaError_t err;

    bufSize = m_color.rowStrideInBytes * m_color.height;

    if (!m_color.data)
    {
        m_lastError = "No color buffer allocated for upload";
        return true;
    }

    err = cudaMemcpy((void*)m_color.data, color,
                                    bufSize, ::cudaMemcpyHostToDevice);
    if (err != cudaSuccess)
    {
        return true;
    }

    if (!albedo)
    {
        return false;
    }

    bufSize = m_albedo.rowStrideInBytes * m_albedo.height;

    if (!m_albedo.data)
    {
        m_lastError = "No albedo buffer allocated for upload";
        return true;
    }

    err = cudaMemcpy((void*)m_albedo.data, albedo,
        bufSize, ::cudaMemcpyHostToDevice);
    if (err != cudaSuccess)
    {
        return true;
    }

    if (!normals)
    {
        return false;
    }

    bufSize = m_normals.rowStrideInBytes * m_normals.height;

    if (!m_normals.data)
    {
        m_lastError = "No normal buffer allocated for upload";
        return true;
    }

    err = cudaMemcpy((void*)m_normals.data, normals,
        bufSize, ::cudaMemcpyHostToDevice);
    if (err != cudaSuccess)
    {
        return true;
    }

    return false;
}

bool
BlenderOptiXDenoiser::download(void)
{
    if (!m_outHostBuffer)
    {
        m_lastError = "No host buffer allocated";
        return true;
    }
    size_t bufSize = m_output.rowStrideInBytes * m_output.height;

    if (bufSize > m_outHostBufferSize)
    {
        m_lastError = "Host buffer not large enough";
        return true;
    }

    cudaError_t err = cudaMemcpy((void*)m_outHostBuffer,
                                (void*)m_output.data, bufSize,
                                ::cudaMemcpyDeviceToHost);
    return err != cudaSuccess;
}

#endif
