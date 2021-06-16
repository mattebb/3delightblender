/*
** Copyright (c) Pixar.  All rights reserved.  This program or
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


#include <vector>
#include <array>
#include <stdlib.h>
#include "libndspy/Dspy.h"

#ifdef OSX
#include <GL/glew.h>
#else
#include <GL/glew.h>
#endif

// New display architecture support
#include "display/renderoutput.h"
#include "display/display.h"

#ifndef OSX
// For OptiX denoiser
#include "BlenderOptiXDenoiser.h"
#endif

struct BlenderImage
{
    BlenderImage()
    {
        isReady = false;
        sampleCountOffset = -1;
        isXpu = false;
        isDirty = false;
        framebuffer = nullptr;
        denoiseFrameBuffer = nullptr;
    }

    int width;
    int height;
    int cropXMin;
    int cropYMin;
    int cropWidth;
    int cropHeight; 
    int arXMin;
    int arXMax;
    int arYMin;
    int arYMax;
    int channels;
    int bytesPerSample;
    int entrysize;
    int entrytype;
    bool useActiveRegion;
    unsigned char* framebuffer;
    unsigned char* denoiseFrameBuffer;
    size_t size;
    GLuint texture_id;
    bool isDirty;
    int use_denoiser;
#ifndef OSX
    BlenderOptiXDenoiser blenderDenoiser;
#endif    
    
    // for XPU
    bool isXpu;
    bool isReady;
    size_t   sampleCountOffset;
    std::vector<display::RenderOutput> renderOutputs;
    std::vector<size_t> channelOffsets;
    const uint8_t* surface;
    display::RenderOutput::DataType type;
    size_t noutputs;

    // These two aren't currently used
    // but are needed if we decide to use a
    // fragment shader
    size_t ciindex;
    size_t aindex;    

};
    
class DisplayBlender : public display::Display
{
public:
    DisplayBlender(const pxrcore::UString name, const pxrcore::ParamList& params);
    ~DisplayBlender();

    /// Display interface
    bool Rebind(const uint32_t width, const uint32_t height,
                const char* srfaddrhandle, const void* srfaddr,
                const size_t srfsizebytes, const size_t samplecountoffset,
                const size_t* offsets, const display::RenderOutput* outputs,
                const size_t noutputs);

    void Close();

    void Notify(const uint32_t iteration, const uint32_t totaliterations,
                const NotifyFlags flags, const pxrcore::ParamList& metadata);

private:
    void WriteBuffer(const uint32_t width, const uint32_t height,
                    const size_t* offsets,
                    const display::RenderOutput* outputs, const size_t noutputs, const float* weights);



    const static size_t       kInvalidOffset = size_t(-1);

    pxrcore::UString m_name;

    BlenderImage*                  m_image;
};

static std::vector<BlenderImage*> s_blenderImages;

bool DenoiseBuffer(BlenderImage* blenderImage)
{
#ifndef OSX
    if (blenderImage->use_denoiser)
    {
        bool failed = false;
        const void* quiet;
        failed = blenderImage->blenderDenoiser.DenoiseBuffer((void*) blenderImage->framebuffer, 
                                            blenderImage->width,
                                            blenderImage->height,
                                            blenderImage->channels,
                                            quiet
                                            );
        if (!failed)
        {
            memcpy(blenderImage->denoiseFrameBuffer, quiet, blenderImage->size);
            blenderImage->blenderDenoiser.UnmapResult();
            return true;
        }
    }
#endif

    return false;
}

// Copy from the XPU shared memory framebuffer to our framebuffer
void CopyXpuBuffer(BlenderImage* blenderImage)
{
    const float* weights = reinterpret_cast<const float*>(blenderImage->surface + blenderImage->sampleCountOffset);

    size_t resolution = blenderImage->width * blenderImage->height;

    float* linebuffer = new float[blenderImage->width * blenderImage->entrysize];

    /* For each pixel ... */
    size_t pixel = 0;
    for (size_t y = 0; y < blenderImage->height; ++y)
    {
        size_t outchannel = 0;
        for (size_t x = 0; x < blenderImage->width; ++x)
        {
            /* Compute reciprical, which we'll use to divide each pixel intensity by */
            float rcp = 1.f / weights[pixel];

            /* Itterate through our render outputs */
            for (size_t roi = 0; roi < blenderImage->noutputs; ++roi)
            {
                const display::RenderOutput& ro = blenderImage->renderOutputs[roi];
                const size_t ofs = blenderImage->channelOffsets[roi];
                const float* floatData = reinterpret_cast<const float*>(blenderImage->surface + ofs);

                /* For each channel in the current render output */
                for (size_t c = 0; c < ro.nelems; ++c)
                {
                    float res = 0.0;
                    // NB - we don't want to average integer values. Instead,
                    // we expect the renderer to have applied a rule such as
                    // overwrite, max or min to preserve precision and avoid
                    // nonesense values at pixels were multiple integer ids
                    // are written by differing primitives
                    if (blenderImage->type == display::RenderOutput::DataType::kDataTypeUInt)
                    {
                        res = floatData[pixel];
                    }
                    else
                    {
                        res = floatData[pixel] * rcp;
                    }
                    linebuffer[outchannel] = res;

                    /* Move data pointer to next channel */
                    floatData += resolution;

                    outchannel++;
                }
            }
            pixel++;
        }
        unsigned char* fb = blenderImage->framebuffer
                          + (y * (blenderImage->width * blenderImage->entrysize));
                         
        memcpy(fb, (unsigned char*) linebuffer, blenderImage->width * blenderImage->entrysize);

    }
    blenderImage->isDirty = true;
    delete[] linebuffer;
}

// Generate the GL texture from our float buffer
void GenerateTexture(BlenderImage* blenderImage)
{
    float* buffer = (float*) blenderImage->framebuffer;
    if (DenoiseBuffer(blenderImage))
    {
        buffer = (float*) blenderImage->denoiseFrameBuffer;
    }
    glGenTextures(1, &blenderImage->texture_id);
    glBindTexture(GL_TEXTURE_2D, blenderImage->texture_id);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA32F,
        static_cast<GLsizei>(blenderImage->width),
        static_cast<GLsizei>(blenderImage->height),
        0,
        GL_RGBA,
        GL_FLOAT,
        buffer); 
    glBindTexture(GL_TEXTURE_2D, 0);
}

extern "C" {

// Return the number of channels for this display
PRMANEXPORT
int GetNumberOfChannels(size_t pos)
{
    if (s_blenderImages.empty() || pos >= s_blenderImages.size())
        return -1;

    BlenderImage* blenderImage = s_blenderImages[pos];
    if (blenderImage == nullptr)
        return -1;

    return blenderImage->channels; 
}

// Return the float buffer for this display
PRMANEXPORT
float* GetFloatFramebuffer(size_t pos)
{
    if (s_blenderImages.empty() || pos >= s_blenderImages.size())
        return nullptr;

    BlenderImage* blenderImage = s_blenderImages[pos];
    
    if (blenderImage == nullptr)
        return nullptr;

    if (blenderImage->isXpu && blenderImage->isDirty)
    {
        CopyXpuBuffer(blenderImage);
    }

    if (DenoiseBuffer(blenderImage)) {
        return (float*) blenderImage->denoiseFrameBuffer;                  
    }
    return (float*) blenderImage->framebuffer;                  
}

// Return the active region that RenderMan is currently working on
PRMANEXPORT
void GetActiveRegion(size_t pos, int& arXMin, int& arXMax, int& arYMin, int& arYMax)
{
    if (s_blenderImages.empty() || pos >= s_blenderImages.size())
        return;

    BlenderImage* blenderImage = s_blenderImages[pos];
    
    if (blenderImage == nullptr)
        return;

    if (blenderImage->useActiveRegion)
    {
        arXMin = blenderImage->arXMin;
        arXMax = blenderImage->arXMax;
        arYMin = blenderImage->arYMin;
        arYMax = blenderImage->arYMax;    
    }
}

// DrawBufferToBlender creates a GL texture that then can be given to 
// Blender to draw into their viewport. It is expected that this function 
// will be called from python via the ctypes module, in the view_draw()
// callback for a RenderEngine addon.
//
// Code based on the Simple RenderEngine example in Blender docs:
// https://docs.blender.org/api/blender2.8/bpy.types.RenderEngine.html
PRMANEXPORT
void DrawBufferToBlender(int viewWidth, int viewHeight)
{
    if (s_blenderImages.empty())
    {
        //fprintf(stderr, "d_blender: images vector empty\n");
        return;
    }
   
    // for the viewport, we only draw the first s_blenderImage
    // and use PxrCopyAOVSampleFilter to switch between channels
    BlenderImage* blenderImage = s_blenderImages[0];

    if (blenderImage == nullptr)
    {
        //fprintf(stderr, "d_blender: cannot find first image\n");
        return;
    }

    GLenum err = glewInit();
    if (GLEW_OK != err)
    {
        fprintf(stderr, "d_blender: glewInit failed\n");
        return;
    }    

    if (blenderImage->isXpu && blenderImage->isDirty)
    {
        CopyXpuBuffer(blenderImage);
        GenerateTexture(blenderImage);
    }
    
    else
    {
        if (!blenderImage->framebuffer)
        {
            return;
        }

        if (blenderImage->isDirty)
        {
            GenerateTexture(blenderImage);
            blenderImage->isDirty = true;
        }

    }

    std::array<GLfloat, 8> position = {0.0f,              0.0f,
                                       (float) viewWidth, 0.0f,
                                       (float) viewWidth, (float) viewHeight,
                                       0.0f,              (float) viewHeight};
    std::array<GLfloat, 8> texture_coords = {0.0, 1.0, 1.0, 1.0,  
                                            1.0, 0.0,  0.0, 0.0};

    GLuint vertex_array;
    std::array<GLint, 2> vertex_buffer;

    GLuint   texcoord_location;
    GLuint   position_location;

    GLint shader_program_id;
    GLuint texture_vbo_id;
    GLuint vertex_vbo_id;

    // Get shader program set by Blender.
    glGetIntegerv(GL_CURRENT_PROGRAM, &shader_program_id);

    // Generate vertex array
    glGenVertexArrays(1, &vertex_array);
    glBindVertexArray(vertex_array);

    texcoord_location = glGetAttribLocation(shader_program_id, "texCoord");
    position_location = glGetAttribLocation(shader_program_id, "pos");
  
    glEnableVertexAttribArray(texcoord_location);
    glEnableVertexAttribArray(position_location);

    glGenBuffers(1, &texture_vbo_id);
    glBindBuffer(GL_ARRAY_BUFFER, texture_vbo_id);
    glBufferData(GL_ARRAY_BUFFER, texture_coords.size() * sizeof(float), 
                 &texture_coords[0], GL_STATIC_DRAW);
    glVertexAttribPointer(texcoord_location, 2, GL_FLOAT, GL_FALSE, 
                          2 * sizeof(float), reinterpret_cast<void*>(0));        

    glGenBuffers(1, &vertex_vbo_id);
    glBindBuffer(GL_ARRAY_BUFFER, vertex_vbo_id);
    glBufferData(GL_ARRAY_BUFFER, position.size() * sizeof(float), 
                 &position[0], GL_STATIC_DRAW);
    glEnableVertexAttribArray(position_location);
    glVertexAttribPointer(position_location, 2, GL_FLOAT, GL_FALSE, 
                          2 * sizeof(float), reinterpret_cast<void*>(0));

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
    
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, blenderImage->texture_id);
    glBindVertexArray(vertex_array);
    glDrawArrays(GL_TRIANGLE_FAN, 0, 4);
    glBindVertexArray(0);
    glDeleteVertexArrays(1, &vertex_array);
    glBindTexture(GL_TEXTURE_2D, 0); 
    glDeleteTextures(1, &blenderImage->texture_id);
}
} // extern "C"


PtDspyError
DspyImageOpen(
    PtDspyImageHandle* ppvImage,
    const char* drivername,
    const char* filename,
    int width,
    int height,
    int paramCount,
    const UserParameter* parameters,
    int formatCount,
    PtDspyDevFormat* format,
    PtFlagStuff* flagstuff)
{
    char* cformat = (char*)"float32";
    DspyFindStringInParamList("format", &cformat, paramCount, parameters);

    /* Fill out initial image data */
    static PtDspyDevFormat _aFormat[] =
        {
            { R"(Ci\.[\d]{3}\.r|r|R)", PkDspyNone },
            { R"(Ci\.[\d]{3}\.g|g|G)", PkDspyNone },
            { R"(Ci\.[\d]{3}\.b|b|B)", PkDspyNone },
            { R"(a\.[\d]{3}|a|A)", PkDspyNone },
            { R"(z\.[\d]{3}|z|Z)", PkDspyNone },
        };
    DspyReorderFormattingRE(formatCount,
                            format,
                            5,
                            _aFormat);


    int count = 2;
    int origin[2];
    origin[0] = 0;
    origin[1] = 0;
    DspyFindIntsInParamList("origin", &count, origin, paramCount, parameters);

    int originalSize[2];
    originalSize[0] = 0;
    originalSize[1] = 0;
    DspyFindIntsInParamList("OriginalSize", &count, originalSize, paramCount, parameters);


    BlenderImage* blenderImage = new BlenderImage();
    blenderImage->width = originalSize[0]; 
    blenderImage->height = originalSize[1];
    blenderImage->cropXMin = origin[0];
    blenderImage->cropYMin = origin[1];
    blenderImage->cropWidth = width;
    blenderImage->cropHeight = height;

    blenderImage->channels = formatCount;

    // If quantization is enabled, force to 1 byte output, else float
    if (!strcmp(cformat, "uint8")) {
        blenderImage->bytesPerSample = 1;
        blenderImage->entrytype = PkDspyUnsigned8;
    } else if (!strcmp(cformat, "uint16")) {
        blenderImage->bytesPerSample = 2;
        blenderImage->entrytype = PkDspyUnsigned16;
    } else {
        blenderImage->bytesPerSample = 4;
        blenderImage->entrytype = PkDspyFloat32;
    }

    if (blenderImage->width != blenderImage->cropWidth || blenderImage->height != blenderImage->cropHeight)
    {
        unsigned int crop[4];

        crop[0] = blenderImage->cropXMin;
        crop[1] = crop[0] + blenderImage->cropWidth + 1;
        crop[2] = blenderImage->cropYMin;
        crop[3] = crop[2] + blenderImage->cropHeight + 1;

        blenderImage->cropXMin = crop[0];
        blenderImage->cropYMin = crop[2];
        blenderImage->cropWidth = crop[1] - crop[0];
        blenderImage->cropHeight = crop[3] - crop[2];
    }

    blenderImage->entrysize = blenderImage->bytesPerSample * formatCount;

    int use_denoiser = 0;
    
#ifndef OSX
    count = 1;
    DspyFindIntsInParamList("use_optix_denoiser", &count, &use_denoiser, paramCount, parameters);
    blenderImage->use_denoiser = use_denoiser;
#endif

    /* Reserve a framebuffer */
    blenderImage->size = blenderImage->width * blenderImage->height * blenderImage->entrysize;
    blenderImage->framebuffer = (unsigned char*) std::malloc(blenderImage->size);
    if (use_denoiser)
    {
        blenderImage->denoiseFrameBuffer = (unsigned char*) std::malloc(blenderImage->size);
    }

    *ppvImage = blenderImage;
    s_blenderImages.push_back(blenderImage);

    return PkDspyErrorNone;
}


PtDspyError
DspyImageQuery(
    PtDspyImageHandle pvImage,
    PtDspyQueryType querytype,
    int datalen,
    void* data)
{
    BlenderImage* blenderImage = (BlenderImage*)pvImage;
    if (0 >= datalen || 0 == data)
        return PkDspyErrorBadParams;

    switch (querytype)
    {
        case PkOverwriteQuery:
        {
            PtDspyOverwriteInfo overwriteInfo;
            if (size_t(datalen) > sizeof(overwriteInfo))
                datalen = sizeof(overwriteInfo);
            overwriteInfo.overwrite = 1;
            overwriteInfo.interactive = 1;
            memcpy(data, &overwriteInfo, datalen);
            return PkDspyErrorNone;
        }
        case PkRedrawQuery:
        {
            PtDspyRedrawInfo redrawInfo;
            if (size_t(datalen) > sizeof(redrawInfo))
                datalen = sizeof(redrawInfo);
            redrawInfo.redraw = 1;
            memcpy(data, &redrawInfo, datalen);
            return PkDspyErrorNone;
        }
        case PkSizeQuery:
        {
            PtDspySizeInfo sizeInfo;

            if (size_t(datalen) > sizeof(sizeInfo))
                datalen = sizeof(sizeInfo);

            sizeInfo.width = blenderImage->cropWidth; 
            sizeInfo.height = blenderImage->cropHeight;
            sizeInfo.aspectRatio = 1.0f;

            memcpy(data, &sizeInfo, datalen);
            return PkDspyErrorNone;
        }
        case PkMultiResolutionQuery:
        {
            PtDspyMultiResolutionQuery* query = 
                                    (PtDspyMultiResolutionQuery*)data;

            /* update datalen with our perception of query's size */
            if (datalen > sizeof(*query))
            {
                datalen = sizeof(*query);
            }

            query->supportsMultiResolution = 1;
            return PkDspyErrorNone;
        }        
        default:
        {
            return PkDspyErrorUnsupported;
        }
    }
}

PtDspyError
DspyImageData(
    PtDspyImageHandle pvImage,
    int xmin,
    int xmax_plus_1,
    int ymin,
    int ymax_plus_1,
    int entrysize,
    const unsigned char* data)
{
    BlenderImage* blenderImage = (BlenderImage*)pvImage;
    int width = (blenderImage->cropXMin + xmax_plus_1) - (blenderImage->cropXMin + xmin);
    int height = (blenderImage->cropYMin + ymax_plus_1) - (blenderImage->cropYMin + ymin);
    for (int y = 0; y < height; ++y) {
        unsigned char* fb = blenderImage->framebuffer
                          + (blenderImage->cropXMin + xmin) 
                          * blenderImage->entrysize
                          + blenderImage->width * (y + ymin + blenderImage->cropYMin) 
                          * blenderImage->entrysize;
        for (int x = 0; x < width; ++x) {
            memcpy(fb, data, blenderImage->entrysize);
            data += entrysize;
            fb += blenderImage->entrysize;
        }
    }

    blenderImage->arXMin = blenderImage->cropXMin + xmin;
    blenderImage->arXMax = blenderImage->cropXMin + xmax_plus_1 - 1;
    blenderImage->arYMin = blenderImage->cropYMin + ymin;
    blenderImage->arYMax = blenderImage->cropYMin + ymax_plus_1 - 1;
    if( blenderImage->arXMin != 0 || 
        blenderImage->arXMax != blenderImage->width-1 || 
        blenderImage->arYMin != 0 || 
        blenderImage->arYMax != blenderImage->height-1 ) 
    {
        blenderImage->useActiveRegion = true;
    } else {
        blenderImage->useActiveRegion = false;
    }
   
    blenderImage->isDirty = true;
    return PkDspyErrorNone;
}

PtDspyError
DspyImageActiveRegion(
    PtDspyImageHandle pvImage,
    int xmin,
    int xmax_plus_one,
    int ymin,
    int ymax_plus_one)
{
    return PkDspyErrorNone;
}

PtDspyError
DspyImageClose(PtDspyImageHandle pvImage)
{
    BlenderImage* blenderImage = (BlenderImage*)pvImage;
    for (auto it = s_blenderImages.begin(); it != s_blenderImages.end(); ++it)
    {
        if (*it == blenderImage)
        {
            s_blenderImages.erase(it);
            break;
        }
    }

    std::free(blenderImage->framebuffer);
    if (blenderImage->denoiseFrameBuffer)
        std::free(blenderImage->denoiseFrameBuffer);

    delete blenderImage;
    return PkDspyErrorNone;
}

PtDspyError
BlenderDspyMetadata(
    PtDspyImageHandle pvImage,
    char* metadata)
{
    return PkDspyErrorNone;
}


DisplayBlender::DisplayBlender(const pxrcore::UString name, const pxrcore::ParamList& params) :
    m_name(name),
    m_image(new BlenderImage)
{
    // parse params
    int use_denoiser = 0;
#ifndef OSX
    params.GetInteger(RtUString("use_optix_denoiser"), use_denoiser);
#endif
    m_image->use_denoiser = use_denoiser;

    s_blenderImages.push_back(m_image);
}

DisplayBlender::~DisplayBlender()
{
}

bool DisplayBlender::Rebind(const uint32_t width, const uint32_t height,
                         const char* srfaddrhandle, const void* srfaddr,
                         const size_t srfsizebytes, const size_t samplecountoffset,
                         const size_t* offsets, const display::RenderOutput* outputs,
                         const size_t noutputs)
{
   size_t nchans = 0;
   size_t pixelsizebytes = 0;
   m_image->renderOutputs.clear();
   m_image->channelOffsets.clear();

   m_image->sampleCountOffset = samplecountoffset;
   m_image->noutputs = noutputs;

   m_image->renderOutputs.insert(m_image->renderOutputs.end(), outputs, outputs + noutputs);
   m_image->channelOffsets.insert(m_image->channelOffsets.end(), offsets, offsets + noutputs);

   for (size_t i = 0; i < noutputs; i++)
   {
       const display::RenderOutput& ro = outputs[i];
       if (strcmp(ro.name.CStr(), "Ci") == 0)
       {
           m_image->ciindex = i;
       }
       if (strcmp(ro.name.CStr(), "a") == 0)
       {
           m_image->aindex = i;
       }
       nchans += ro.nelems;
       pixelsizebytes += 4 * ro.nelems;

       if (ro.datatype != display::RenderOutput::DataType::kDataTypeFloat &&
           ro.datatype != display::RenderOutput::DataType::kDataTypeUInt)
       {
           fprintf(stderr,
                   "d_blender: Unsupported datatype for RenderOutput %s. Supported types "
                   "are Int, Float\n",
                   ro.name.CStr());
           return false;
       }

       if (i == 0)
           m_image->type = ro.datatype;
       else if (ro.datatype != m_image->type)
       {
           fprintf(stderr,
                   "d_blender: Mismatching datatype between RenderOutput %s and previous "
                   "RenderOutput.\n",
                   ro.name.CStr());
           return false;
       }
   }

   m_image->surface = static_cast<const uint8_t*>(srfaddr);    

   // Setup BlenderImage
   m_image->isXpu = true;
   m_image->width = width;
   m_image->height = height;
   m_image->cropXMin = 0;
   m_image->cropYMin = 0;
   m_image->cropWidth = width;
   m_image->cropHeight = height;
   m_image->channels = nchans;
   m_image->entrytype = PkDspyFloat32; // Assume float, might be int32 -- no others are supported
   m_image->entrysize = pixelsizebytes; 

   m_image->size = m_image->width * m_image->height * m_image->entrysize;
   if (m_image->framebuffer)
   {
       std::free(m_image->framebuffer);
   }
   if (m_image->denoiseFrameBuffer)
   {
       std::free(m_image->denoiseFrameBuffer);
   }

   m_image->framebuffer = (unsigned char*) std::malloc(m_image->size);
   if (m_image->use_denoiser)
   {
        m_image->denoiseFrameBuffer = (unsigned char*) std::malloc(m_image->size);
   }
   return true; 
}

void DisplayBlender::Close()
{
    m_image->isReady = false;
    m_image->sampleCountOffset = -1;
    if (m_image->framebuffer)
    {
        std::free(m_image->framebuffer);
    }
    if (m_image->denoiseFrameBuffer)
    {
        std::free(m_image->denoiseFrameBuffer);
    }
}

void DisplayBlender::Notify(const uint32_t iteration, const uint32_t totaliterations,
                         const NotifyFlags flags, const pxrcore::ParamList& /*metadata*/)
{
    if (!m_image->isReady)
    {
        // we're now ready to copy from the
        // shared memory
        m_image->isReady = true;
    }
    m_image->isDirty = true;

}

static void closeBlenderImages()
{
    if (!s_blenderImages.empty())
    {
        s_blenderImages.clear();
    }
}

// New display architecture factory entrypoints
extern "C" {

PRMANEXPORT
display::Display* CreateDisplay(const pxrcore::UString& name, const pxrcore::ParamList& params,
                                const pxrcore::ParamList&)
{
    return new DisplayBlender(name, params);
}

PRMANEXPORT
void DestroyDisplay(const display::Display* p)
{
    closeBlenderImages();
    delete p;
}

}  // extern "C"
