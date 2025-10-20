# Domintell EcoPilot Integration for Home Assistant

This integration allows Home Assistant to seamlessly connect with your Domintell EcoPilot devices.

It is engineered to collect data directly from your EcoPilot products, converting this information into functional sensors within your Home Assistant system.

Its main purpose is to give you the tools to closely monitor your consumption of electricity, gas, heating oil, and water. Making it it the indispensable component for refining your overall energy management strategy.

Thanks to this gateway, the information thus centralized can be optimally utilized and contextualized within Home Assistant's Energy dashboard.

## High-Level Description

EcoPilot by Domintell is a comprehensive energy management and optimization solution designed for both private individuals and professionals (from SMEs to heavy industry) wishing to regain total control over their building or site.

The service positions itself as an all-in-one tool that goes beyond simple data visualization. It enables real-time tracking of all resources (electricity, gas, water, fuel oil, etc.), as well as production and storage (such as rainwater).

## Installation

### Prerequisites

- A Domintell EcoPilot device.
- Home Assistant installation.
- Knowledge of your Domintell EcoPilot device configuration.

### Installation Steps

1.  **Using HACS (Home Assistant Community Store - Recommended):**
    - Search for "Domintell EcoPilot" in the Integrations section of HACS.
    - Click "Install."
2.  **Manual Installation:**
    - Download the latest release from the GitHub repository.
    - Copy the `domintell_ecopilot` folder into your Home Assistant's `custom_components` directory.
    - Restart Home Assistant.

## Configuration

To add the Domintell EcoPilot integration to your Home Assistant instance, use this My button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Domintell&repository=ha_domintell_ecopilot&category=Integration)

Domintell EcoPilot devices can be auto-discovered by Home Assistant. If an instance was found, it will be shown as Discovered. You can then set it up right away.

### Manual configuration steps

If it wasn’t discovered automatically, don’t worry! You can set up a manual integration entry:

- Browse to your Home Assistant instance.
- Go to Settings > Devices & Services.
- In the bottom right corner, select the Add Integration button.
- From the list, select Domintell EcoPilot.
- Follow the instructions on screen to complete the setup.

### Installation Parameters

During installation, you will be prompted for:

- **Host:** The IP address or hostname of your Domintell EcoPilot device.

## Supported Devices

This integration supports the following EcoPilot devices:

- **tankSense:**

- **ecoDrive-P1:**

- **Comming soon:**
  - ecoP1
  - ecoPlug
  - hubSense

## Identify

The identify button can be pressed to let the status light blink for a few seconds.

## Known limitations

- **AAABBBCC:** TODO

## Troubleshooting

You can’t find your device or there is an error during inclusion. This can be caused by the following:

- **Connection Issues:**
  1.  Verify the IP address/hostname of your Domintell EcoPilot device. Check your network connectivity.
  2.  If the device and the Home Assistant instance are on different networks, ensure that the network configuration allows communication between them. This may involve configuring port forwarding, firewall rules, or VPN settings.

## Remove integration

This integration follows standard integration removal.

TO REMOVE AN INTEGRATION INSTANCE FROM HOME ASSISTANT

- Go to Settings > Devices & services and select the integration card.
- From the list of EcoPilot devices, select the integration instance you want to remove.
- Next to the entry, select the three-dot menu. Then, select Delete.
