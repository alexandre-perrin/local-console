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
