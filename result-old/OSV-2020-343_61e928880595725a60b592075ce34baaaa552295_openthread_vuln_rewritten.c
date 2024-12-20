uint32_t ChannelMaskTlv::GetChannelMask(const Message &aMessage)
{
    uint32_t       mask = 0;
    ChannelMaskTlv channelMaskTlv;

    SuccessOrExit(GetTlv(aMessage, kChannelMask, sizeof(channelMaskTlv), channelMaskTlv));
    mask = channelMaskTlv.GetChannelMask();

exit:
    return mask;
}