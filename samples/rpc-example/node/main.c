/*
 * Copyright 2024 Sony Semiconductor Solutions Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "evp/sdk.h"
#include "logger.h"
#include <assert.h>
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include "parson.h"

static const char *module_name = "Source";
static struct EVP_client *h;
static char *g_publish_to = "my-topic";
static int r = 0;
static int g = 0;
static int b = 0;

struct telemetry_data {
    struct EVP_telemetry_entry entries[1];
};

static void telemetry_cb(EVP_TELEMETRY_CALLBACK_REASON reason, void *userData) {
    assert(userData != NULL);
    struct telemetry_data *d = userData;
    assert(d->entries[0].key != NULL);
    assert(d->entries[0].value != NULL);

    free((void *)d->entries[0].key);
    free((void *)d->entries[0].value);
    free(d);
}

static void send_telemetry() {
    struct telemetry_data *d = malloc(sizeof(*d));

    d->entries[0].key = strdup(g_publish_to);
    char *buf = NULL;
    asprintf(&buf, "{\"r\": \"%d\", \"g\": \"%d\", \"b\": \"%d\"}", r, g, b);
    d->entries[0].value = buf;

    EVP_RESULT result = EVP_sendTelemetry(h, d->entries, 1, telemetry_cb, d);
    assert(result == EVP_OK);
}

void rpc_cb(EVP_RPC_ID id, const char *methodName, const char *params, void *userData) {
    LOG_INFO("%s", methodName);
    LOG_INFO("%s", params);
    JSON_Value *schema = json_parse_string(params);
    JSON_Object *object = json_value_get_object(schema);
    const char *rgb = json_object_dotget_string(object, "rgb");
    sscanf(rgb, "%02x%02x%02x", &r, &g, &b);
    json_value_free(schema);
    LOG_INFO("r=%d g=%d b=%d", r, g, b);
}

/* The variables and the EVP configuration callback below implement
 * a simple loopback (or "echo") of a configuration message as
 * a telemetry message
*/
static char *g_topic = NULL;
static char *g_blob = NULL;
static size_t g_blob_len;

static void
config_cb(const char *topic, const void *config, size_t configlen,
      void *userData)
{
    LOG_INFO("%s: Received Configuration (topic=%s, size=%zu)\n",
             module_name, topic, configlen);

    free(g_blob);
    free(g_topic);

    /* Note: +1 to avoid 0-sized malloc */
    g_blob = malloc(configlen + 1);
    assert(g_blob != NULL);
    memcpy(g_blob, config, configlen);
    g_blob[configlen] = 0;

    g_topic = strdup(topic);
    assert(g_topic != NULL);

    g_blob_len = configlen;
}

long
get_time_ms(void)
{
    struct timespec t;
    int ret;

    ret = clock_gettime(CLOCK_REALTIME, &t);
    assert(ret != -1);
    long tms = t.tv_sec * 1000 + t.tv_nsec / 1000000;
    return tms;
}

int main() {
    LOG_INFO("%s Started!", module_name);
    h = EVP_initialize();

    EVP_setRpcCallback(h, rpc_cb, NULL);
    EVP_setConfigurationCallback(h, config_cb, NULL);

    /* Will send a periodic telemetry message every 2 seconds */
    long tic = get_time_ms();
    long toc = tic + 2000;

    for (;;) {
        EVP_RESULT result = EVP_processEvent(h, 1000);
        if (result == EVP_SHOULDEXIT) {
            LOG_INFO("%s: exiting the main loop", module_name);
            free(g_topic);
            free(g_blob);
            g_topic = NULL;
            g_blob = NULL;
            break;
        }

        tic = get_time_ms();
        if (tic >= toc) {
            toc += 2000;
            LOG_INFO("Sending telemetry...");
            send_telemetry();
        }

        if (g_blob_len) {
            LOG_INFO("%s: Sending echoing telemetry (topic=%s, size=%zu)\n",
                     module_name, g_topic, g_blob_len);
            struct telemetry_data *d = malloc(sizeof(*d));
            d->entries[0].key = strdup(g_topic);
            char *buf = NULL;
            asprintf(&buf, "{\"data\": \"%s\"}", g_blob);
            d->entries[0].value = buf;
            result = EVP_sendTelemetry(h, d->entries, 1, telemetry_cb, d);
            g_blob_len = 0;
            assert(result == EVP_OK);
        }
    }
    return 0;
}
