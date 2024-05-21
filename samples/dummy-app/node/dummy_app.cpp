// Copyright 2024 Sony Semiconductor Solutions Corp.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

#include "evp/sdk.h"
#include "logger.h"
#include "vision_app_public.h"

#define DUMMY_JSON "{\"my_topic\": 1234}"

static const char* stream_key = SENSCORD_STREAM_KEY_IMX500_IMAGE;

static void SendDataDoneCallback(void *buf_addr, void *private_data, SessResult send_data_ret) {
    LOG_INFO("SessDataCallback called");
    free(buf_addr);
}

int main(int argc, char *argv[]) {
    struct EVP_client* h = NULL;
    senscord_core_t core = NULL;
    senscord_stream_t stream = NULL;
    int32_t ret = -1;
    char *telemetry = NULL;

    LOG_INFO("Application running...");
    SessResult sess_ret = SessInit();
    if (sess_ret != kSessOK) {
        LOG_ERR("SessInit : sess_ret=%d", sess_ret);
        return -1;
    }

    LOG_DBG("SessRegisterSendDataCallback");
    sess_ret = SessRegisterSendDataCallback(SendDataDoneCallback, NULL);
    if (sess_ret != kSessOK) {
        LOG_ERR("SessRegisterSendDataCallback : sess_ret=%d", sess_ret);
        goto sess_exit;
    }

    LOG_DBG("senscord_core_init");
    ret = senscord_core_init(&core);
    if (ret < 0) {
        LOG_ERR("senscord_core_init : ret=%d", ret);
        goto unreg;
    }

    LOG_DBG("senscord_core_open_stream");
    ret = senscord_core_open_stream(core, stream_key, &stream);
    if (ret < 0) {
        LOG_ERR("senscord_core_open_stream : ret=%d", ret);
        goto exit;
    }

    LOG_DBG("senscord_stream_start");
    ret = senscord_stream_start(stream);
    if (ret < 0) {
        LOG_ERR("senscord_stream_start : ret=%d", ret);
        goto close;
    }

    for (;;) {
        LOG_DBG("New iteration");
        EVP_RESULT evp_ret = EVP_processEvent(h, 0);
        if (evp_ret == EVP_SHOULDEXIT) {
            LOG_INFO("Should exit vision app");
            break;
        }

        LOG_DBG("Waiting for frame");
        senscord_frame_t frame;
        ret = senscord_stream_get_frame(stream, &frame, -1);
        if (ret < 0) {
            LOG_ERR("senscord_stream_get_frame : ret=%d", ret);
            struct senscord_status_t status;
            senscord_get_last_error(&status);
            if (status.cause == SENSCORD_ERROR_TIMEOUT) {
                continue;
            }
            else {
                break;
            }
        }

        LOG_DBG("Get output tensor");
        senscord_channel_t channel;
        uint32_t channel_id_output_tensor = SENSCORD_CHANNEL_ID_OUTPUT_TENSOR;
        ret = senscord_frame_get_channel_from_channel_id(frame, channel_id_output_tensor, &channel);
        if (ret < 0) {
            LOG_ERR("senscord_frame_get_channel_from_channel_id : ret=%d", ret);
            goto release;
        }

        LOG_DBG("Get output tensor buffer");
        struct senscord_raw_data_t raw_data;
        ret = senscord_channel_get_raw_data(channel, &raw_data);
        if (ret < 0) {
            LOG_ERR("senscord_channel_get_raw_data : ret=%d", ret);
            goto release;
        }

        LOG_INFO("raw_data.address:%p", raw_data.address);
        LOG_INFO("raw_data.size:%zu", raw_data.size);
        LOG_INFO("raw_data.timestamp:%llu", raw_data.timestamp);
        LOG_INFO("raw_data.type:%s", raw_data.type);

        telemetry = strdup(DUMMY_JSON);
        if (telemetry == NULL) {
            LOG_ERR("strdup error");
            goto release;
        }

        LOG_DBG("Send data");
        sess_ret = SessSendData((const void*)telemetry, strlen(telemetry), raw_data.timestamp);
        if (sess_ret == kSessOK) {
            /* Do Nothing */
        }
        else if (sess_ret == kSessNotStreaming) {
            LOG_DBG("camera not streaming : sess_ret=%d", sess_ret);
            free(telemetry);
        }
        else {
            LOG_ERR("SessSendData : sess_ret=%d", sess_ret);
            free(telemetry);
        }
release:
        ret = senscord_stream_release_frame(stream, frame);
        if (ret < 0) {
            LOG_ERR("senscord_stream_release_frame : ret=%d", ret);
            break;
        }
    }

    ret = senscord_stream_stop(stream);
    if (ret < 0) {
        LOG_ERR("senscord_stream_stop : ret=%d", ret);
    }
close:
    ret = senscord_core_close_stream(core, stream);
    if (ret < 0) {
        LOG_ERR("senscord_core_close_stream : ret=%d", ret);
    }
exit:
    ret = senscord_core_exit(core);
    if (ret < 0) {
        LOG_ERR("senscord_core_exit : ret=%d", ret);
    }
unreg:
    sess_ret = SessUnregisterSendDataCallback();
    if (sess_ret != kSessOK) {
        LOG_ERR("SessUnregisterSendDataCallback : sess_ret=%d", sess_ret);
    }
sess_exit:
    sess_ret = SessExit();
    if (sess_ret != kSessOK) {
        LOG_ERR("SessExit : sess_ret=%d", sess_ret);
    }
    return 0;
}
