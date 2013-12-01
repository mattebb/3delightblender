/*
# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2012 Matt Ebb
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
#
# ##### END MIT LICENSE BLOCK #####
*/

#include "util.h"

class diffuse (
                  shader shdColor = null;
                  float Kd = 0.5;
                  )
{
    public constant string type = "diffuse";

    shadingGeo SG;
    varying color surfColor = 1;

    public void begin()
    {
        SG->P = P;
        SG->Ns = shadingnormal(N);
        SG->I = I;
        SG->dPdu = dPdu;
        SG->dPdv = dPdv;
        SG->Cs = Cs;

        if( shdColor != null )
            surfColor = shdColor->getColor(P);

    }

    public void surface(output color Ci, Oi)
    {
        Ci = 0;
        illuminance(SG->P, SG->Ns, PI/2)
        {
            //extern vector L;
            //extern vector Cl;
            Ci += bsdf(L, SG->Ns) * Cl;
        }

        Ci *= surfColor;
        Oi = 1.0;
    }
}
