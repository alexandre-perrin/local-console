# Manual Testing

## Introduction

This documentation outlines the manual tests conducted directly from the GUI, emphasizing hands-on exploration and validation of the system's behavior through interactive testing.

## Prerequisites

Before initiating manual testing, ensure the following prerequisites are in place:

- Python 3.11 (or higher)
- pip
- mosquitto (2.0.11 tested)
- flatc (23.1.21 tested)
- wedge-cli

### Tested Environment

- Operating System: Ubuntu 22.04

### Firmware

- Type 3 Firmware: [vD7.00.F3](https://github.com/SonySemiconductorSolutions/EdgeAIPF.smartcamera.type3.mirror/releases/tag/vD7.00.F3)
  - Modified [sec_swaf_key.h](https://github.com/midokura/EdgeAIPF.smartcamera.type3.mirror/blob/vD7.00.F3/src/security/sec_swaf_key.h) to incorporate custom keys.

Please note:
- Testing has been conducted on different hardware versions, including Type 3 TS and ES. Unless otherwise specified, both cameras have been tested in each scenario.

## Tested Scenarios

### Open GUI, generate QR, and connect

- Prerequisite
    - GUI is not running yet.
    - No other process is listening to the MQTT port `wedge-cli config get mqtt port`
      -  You can verify it by running `lsof -i :<PORT>`. It should report no entries.
    - Factory reset camera.

Camera: ES

1. Run GUI from the terminal

```
wedge-cli gui
```

![homescreen](assets/homescreen.png)

2. Go to the "Connection" screen

![connection](assets/connection.png)

In this view the user can configure the connection settings.

Notice that,

![connection-qr-message](assets/connection-qr-message.png)

3. Click "Generate"

![connection-qr](assets/connection-qr.png)

4. Show QR to the camera

![connection-established](assets/connection-established.png)

Connection established.

All other tested scenarios assume that the camera is already connected. Either by QR or by flashing the MQTT endpoint and port.

### Streaming view

1. From "Homescreen" go to "Streaming"

![streaming](assets/streaming.png)

2. Click on "Set Streaming"

![streaming-active](assets/streaming-active.png)

Streaming is active. Images will start appearing in the viewer.

3. Stop the preview by clicking on "Set Streaming"

![streaming-inactive](assets/streaming-inactive.png)

Streaming is inactive.

#### Configure where to store images and metadata

1. From "Homescreen" go to "Configuration"

![configuration](assets/configuration.png)

2. Configure "Image dir"

![streaming-roi-reset](assets/streaming-roi-reset.png)

3. Images are accessible from the folder we have specified

![streaming-saved-image](assets/streaming-saved-image.png)

If no path is specified, images and metadata are stored in a temporal folder.

#### Set ROI

1. Click on "Set ROI"

![streaming-roi](assets/streaming-roi.png)

and select a region.

2. Click on "Set Streaming"

![streaming-roi-active](assets/streaming-roi-active.png)

As before, the status will move to active. Images that will be processed on the sensor, and those that we show in the viewer, are cropped in that region.

![streaming-roi-inactive](assets/streaming-roi-inactive.png)

3. Click on "Set Streaming" to disable it

![streaming-roi-reset](assets/streaming-roi-reset.png)

### Flatbuffers configuration

- Prerequisite
    - Before selecting a schema, ensure that the streaming is inactive.

1. Click on the folder icon on the right of the "Schema" field

![configuration-default](assets/configuration-default.png)

2. Move to the directory that contains the classification flatbuffers schema

![configuration-select](assets/configuration-select.png)

3. Select and press "Process schema"

![configuration-result](assets/configuration-result.png)

If the schema is valid, GUI will show "Success!".

Please note:
- Offline tool validates that it is a valid flatbuffers scheme
The offline tool assumes that all output tensors received from now on follow this schema.
- [classification.fbs](https://github.com/SonySemiconductorSolutions/aitrios-sdk-vision-app-dev/blob/49ed0f048f81f0bb9273bde5105566d352deb1f7/tutorials/4_prepare_application/1_develop/sdk/schema/classification.fbs)

### Application deployment

- Prerequisite
    - [classification app](https://github.com/SonySemiconductorSolutions/aitrios-sdk-vision-app-dev/tree/49ed0f048f81f0bb9273bde5105566d352deb1f7/tutorials/4_prepare_application/1_develop/sdk/sample/vision_app/single_dnn/classification) with correct default values:
      - `dnn_output_classes` is set to 1001. Modify [here](https://github.com/SonySemiconductorSolutions/aitrios-sdk-vision-app-dev/blob/49ed0f048f81f0bb9273bde5105566d352deb1f7/tutorials/4_prepare_application/1_develop/sdk/sample/post_process/classification/include/analyzer_classification.h#L26).
    - Compile and sign with ES/TS keys.
    - wasi-sdk 21.0
    - wamrc 1.1.2
    - Before deploying a neural network, ensure that the streaming is inactive.
1. Select app to deploy

![app](assets/app.png)

2. App is deployed

![app-deployed](assets/app-deployed.png)
Please note:
Now there is no way to undeploy the application.
### AI Model Deployment

- Prerequisite
    - Before deploying an AI model, ensure that the streaming is inactive.

Camera: TS
- IMX500 firmware supporting unencrypted AI models is not available.

Find the `network.pkg` [here](https://github.com/SonySemiconductorSolutions/EdgeAIPF.smartcamera.type3.mirror/blob/vD7.00.F3/res/test_data/AImodels/MobilenetV1/network.pkg).

1. Select AI model package

![nn-selected](assets/nn-selected.png)

2. Click on "Deploy"

It will transition to Downloading and Applying,

![nn-updating](assets/nn-updating.png)

and finally, Done.

![nn-ready](assets/nn-ready.png)

The AI model is now ready for use in the Inference view.

### Inference view

- Prerequisite
  - AI model and application deployed.
  - Flatbuffers configured for human-readable output.

Camera: TS
- Same as "AI Model deployment"

1. Go to the "Inference" view

![inference](assets/inference.png)

If Streaming was previously initiated, you will see the input tensor and the raw output tensor.

2. Click on "Set Streaming"

![inference-active](assets/inference-active.png)

At this point, the view will display the metadata sent by the application, rendered in a human-readable format using the flatbuffers schema.

As can be seen, the top-1 class is 838 with a score of 0.83.

In [ImageNet](https://deeplearning.cms.waikato.ac.nz/user-guide/class-maps/IMAGENET/) we have:

- 836: sunglasses
- 837: sunglasses, sunglasses, dark glasses, shades
- 838: sunscreen, sunblock, sunscreen

Therefore, it seems reasonable to think that the AI model is correctly classifying the image because the sunglasses are detected.
