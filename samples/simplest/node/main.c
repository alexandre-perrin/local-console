#include "evp/sdk.h"
#include "logger.h"

static struct EVP_client *h;

int main() {
    LOG_INFO("Started!");
    h = EVP_initialize();

    for (;;) {
        EVP_RESULT result = EVP_processEvent(h, 1000);
        if (result == EVP_SHOULDEXIT) {
            LOG_INFO("Exiting the main loop");
            break;
        }
        LOG_INFO("Iterating...");
    }
    return 0;
}
