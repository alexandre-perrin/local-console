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

#ifndef LOGGER_H
#define LOGGER_H

#include <stdio.h>
#include <string.h>

#define FILENAME                                                          \
    (strrchr(__FILE__, '/') ? strrchr(__FILE__, '/') + 1 : __FILE__)

#define LOG_LEVEL_DEBUG   0 /* Detailed point to analyze errors */
#define LOG_LEVEL_INFO    1 /* Info about process */
#define LOG_LEVEL_WARNING 2 /* Expected fail, not critical */
#define LOG_LEVEL_ERROR   3 /* Unexpected fail (recoverable) */

#if !defined(LOG_LEVEL_ENABLED)
#define LOG_LEVEL_ENABLED 0
#endif

#if LOG_LEVEL_ENABLED <= LOG_LEVEL_ERROR
#define LOG_ERR(fmt, ...)                                                     \
    do {                                                                      \
        printf("[%s:%d ERROR] " fmt, FILENAME, __LINE__, ##__VA_ARGS__);  \
        printf("\n");                                                         \
        fflush(stdout);                                                       \
    } while (0)
#else
#define LOG_ERR(fmt, ...)
#endif

#if LOG_LEVEL_ENABLED <= LOG_LEVEL_WARNING
#define LOG_WARN(fmt, ...)                                                    \
    do {                                                                      \
        printf("[%s:%d WARNING] " fmt, FILENAME, __LINE__,                \
               ##__VA_ARGS__);                                                \
        printf("\n");                                                         \
        fflush(stdout);                                                       \
    } while (0)
#else
#define LOG_WARN(fmt, ...)
#endif
#if LOG_LEVEL_ENABLED <= LOG_LEVEL_INFO
#define LOG_INFO(fmt, ...)                                                    \
    do {                                                                      \
        printf("[%s:%d INFO] " fmt, FILENAME, __LINE__, ##__VA_ARGS__);   \
        printf("\n");                                                         \
        fflush(stdout);                                                       \
    } while (0)
#else
#define LOG_INFO(fmt, ...)
#endif
#if LOG_LEVEL_ENABLED <= LOG_LEVEL_DEBUG
#define LOG_DBG(fmt, ...)                                                     \
    do {                                                                      \
        printf("[%s:%d DEBUG] " fmt, FILENAME, __LINE__, ##__VA_ARGS__);  \
        printf("\n");                                                         \
        fflush(stdout);                                                       \
    } while (0)
#else
#define LOG_DBG(fmt, ...)
#endif

#endif
