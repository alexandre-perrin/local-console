#include "evp/sdk.h"
#include "logger.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static struct EVP_client *h;

int main() {
    LOG_INFO("Started!\n");
    h = EVP_initialize();

    for (;;) {
        EVP_RESULT res = EVP_processEvent(h, 1000);
        if (res == EVP_SHOULDEXIT) {
            LOG_INFO("exiting the main loop\n");
            break;
        }
        LOG_INFO("Sleeping...");
    }
    return 0;
}
