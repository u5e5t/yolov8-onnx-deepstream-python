/*
 * Copyright (c) 2018-2020, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include "nvdsinfer_custom_impl.h"
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define CLIP(a, min, max) (MAX(MIN(a, max), min))
#define CONF_THRESH 0.4
#define VIS_THRESH 0.4
#define NMS_THRESH 0.4

extern "C" bool NvDsInferParseCustomYolo(
    std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
    NvDsInferNetworkInfo const &networkInfo,
    NvDsInferParseDetectionParams const &detectionParams,
    std::vector<NvDsInferObjectDetectionInfo> &objectList);

static constexpr int LOCATIONS = 4;
static constexpr int CLASS = 4;

struct alignas(float) Detection{
    float bbox[LOCATIONS];
    float score;
    int classes;
    // float anchor[ANCHORS];
};


void create_anchor_Yolo(std::vector<Detection>& res, float *output, float conf_thresh, int width, int height, int outsize) {
    // int det_size = sizeof(Detection) / sizeof(float);
    // int rows = outsize / det_size;
    int rows = outsize;
    // std::cout<<rows<<"------------------"<<std::endl;
    for (int i = 0; i < rows; i++){
        // std::cout<<i;
        // std::cout<<"score";
        // std::cout<<&output[det_size * i+0]<<"--"<<&output[det_size * i+1]<<"--"<<&output[det_size * i+2]<<"--"<<&output[det_size * i+3]<<"--"<<std::endl;
        // std::cout<<&output[det_size * i+4]<<"--"<<&output[det_size * i+5]<<"--"<<&output[det_size * i+6]<<"--"<<&output[det_size * i+7]<<"--"<<std::endl;
        // std::cout<<"1____"<<output[i+4*rows]<<"--"<<output[i+5*rows]<<"--"<<output[i+6*rows]<<"--"<<output[i+7*rows]<<"--"<<std::endl;
        // std::cout<<"0____"<<output[i+0*rows]<<"--"<<output[i+1*rows]<<"--"<<output[i+2*rows]<<"--"<<output[i+3*rows]<<"--"<<std::endl;
        // if (output[det_size * i+4] <= conf_thresh && output[det_size * i+5] <= conf_thresh && output[det_size * i+6] <= conf_thresh && output[det_size * i+7] <= conf_thresh ){
        //     continue;
        // }
        float maxscore = 0.0f;
        int maxindex = -1;
        Detection det;
        for(int j=0; j< CLASS; j++){
            float probe = output[i+(4+j)*rows];
            if (probe > maxscore){
                maxscore = probe;
                maxindex = j;
            }
            // det.bbox[j] = CLIP(output[i+j*rows], 0, width - 1);
        }
        if (maxscore < conf_thresh){
            continue;
        }

        float bxc = output[i + rows * 0];
        float byc = output[i + rows * 1];
        float bw = output[i + rows * 2];
        float bh = output[i + rows * 3];
        float x0 = bxc - bw / 2;
        float y0 = byc - bh / 2;
        float x1 = x0 + bw;
        float y1 = y0 + bh;
        det.bbox[0] = CLIP(x0, 0, width - 1);
        det.bbox[1] = CLIP(y0, 0, height - 1);
        det.bbox[2] = CLIP(x1, 0, width - 1);
        det.bbox[3] = CLIP(y1, 0, height - 1);
        det.score = maxscore;
        det.classes = maxindex;

        res.push_back(det);
        
    }
}


static bool NvDsInferParseYolo(std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
                                    NvDsInferNetworkInfo const &networkInfo,
                                    NvDsInferParseDetectionParams const &detectionParams,
                                    std::vector<NvDsInferObjectDetectionInfo> &objectList) {
    
  
    float *output = (float*)(outputLayersInfo[0].buffer);
    int output_size = outputLayersInfo[0].inferDims.d[1];
    // int output_size = outputLayersInfo[0].inferDims.numElements;
    // std::cout<<outputLayersInfo[0].layerName<<"-------------"<<std::endl;
    // outputSize = layer.inferDims.d[1];
    // std::cout<<outputLayersInfo[0].inferDims.d[0]<<"++++++++++++"<<std::endl;
    // std::cout<<outputLayersInfo[0].inferDims.d[1]<<"++++++++++++"<<std::endl;
    std::vector<Detection> temp;
    std::vector<Detection> res;
    create_anchor_Yolo(temp, output, CONF_THRESH, networkInfo.width, networkInfo.height, output_size);
    // std::cout<<"anchor"<<std::endl;
    // nms_and_adapt(temp, res, NMS_THRESH, networkInfo.width, networkInfo.height);
    // std::cout<<"nms"<<std::endl;

    for(auto& r : temp) {
        
        // if(r.score<=VIS_THRESH) continue;
        // std::cout<<r.score[0]<<"--"<<r.score[1]<<"--"<<r.score[2]<<"--"<<r.score[3]<<"--"<<std::endl;
        // if (r.score[0] <= VIS_THRESH && r.score[1] <= VIS_THRESH && r.score[2] <= VIS_THRESH && r.score[3] <= VIS_THRESH ){
        //     continue;
        // }
	    NvDsInferParseObjectInfo oinfo;  
	    oinfo.classId = r.classes;
        // std::cout<<"obj"<<oinfo.classId<<std::endl;
	    oinfo.left    = static_cast<unsigned int>(r.bbox[0]);
	    oinfo.top     = static_cast<unsigned int>(r.bbox[1]);
	    oinfo.width   = static_cast<unsigned int>(r.bbox[2]-r.bbox[0]);
	    oinfo.height  = static_cast<unsigned int>(r.bbox[3]-r.bbox[1]);
	    oinfo.detectionConfidence = r.score;
        // std::cout<<oinfo.classId<<"-----"<<oinfo.detectionConfidence<<std::endl;
        // std::cout<<oinfo.left<<"-----"<<oinfo.top<<std::endl;
        // std::cout<<oinfo.width<<"-----"<<oinfo.height<<std::endl;
        objectList.push_back(oinfo);
        
             
    }
    return true;
}


extern "C" bool NvDsInferParseCustomYolo(
    std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
    NvDsInferNetworkInfo const &networkInfo,
    NvDsInferParseDetectionParams const &detectionParams,
    std::vector<NvDsInferParseObjectInfo> &objectList)
{
    return NvDsInferParseYolo(
        outputLayersInfo, networkInfo, detectionParams, objectList);
}

/* Check that the custom function has been defined correctly */
CHECK_CUSTOM_PARSE_FUNC_PROTOTYPE(NvDsInferParseCustomYolo);
