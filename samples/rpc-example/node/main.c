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

    /* Will send a periodic telemetry message every 2 seconds */
    long tic = get_time_ms();
    long toc = tic + 2000;

    for (;;) {
        EVP_RESULT result = EVP_processEvent(h, 1000);
        if (result == EVP_SHOULDEXIT) {
            LOG_INFO("%s: exiting the main loop", module_name);
            break;
        }

        tic = get_time_ms();
        if (tic >= toc) {
            toc += 2000;
            LOG_INFO("Sending telemetry...");
            send_telemetry();
        }
    }
    return 0;
}
