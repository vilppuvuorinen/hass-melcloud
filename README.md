# melcloudexp

Expiremental fork of the MELCloud integration in Home Assistant.

## How does thing differ from the upstream integration?

I'm glad you asked. Most of the stuff you see here is intended to be merged
back into the upstream Home Assistant. Here you can expect to find features
not yet available in the upstream version or things that are just broken.

Having access to limited range of devices (the range being 1 `AtaDevice`)
makes it a little challenging. It helps a lot to have someone test these
things out on a real device before starting wrestle things to fit the
upstream.

## Setup

Install by copying the `melcloudexp` directory to your `custom_components`
directory. Rest of the setup happens through the UI with a 
`config_flow`. Good times all around.
