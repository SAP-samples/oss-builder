otError Ip6::RemoveMplOption(Message &aMessage)
{
    otError        error = OT_ERROR_NONE;
    Header         ip6Header;
    HopByHopHeader hbh;
    uint16_t       offset;
    uint16_t       endOffset;
    uint16_t       mplOffset = 0;
    uint8_t        mplLength = 0;
    bool           remove    = false;

    offset = 0;
    aMessage.Read(offset, sizeof(ip6Header), &ip6Header);
    offset += sizeof(ip6Header);
    VerifyOrExit(ip6Header.GetNextHeader() == kProtoHopOpts);

    aMessage.Read(offset, sizeof(hbh), &hbh);
    endOffset = offset + (hbh.GetLength() + 1) * 8;
    VerifyOrExit(aMessage.GetLength() >= endOffset, error = OT_ERROR_PARSE);

    offset += sizeof(hbh);

    while (offset < endOffset)
    {
        OptionHeader option;

        aMessage.Read(offset, sizeof(option), &option);

        switch (option.GetType())
        {
        case OptionMpl::kType:
            // if multiple MPL options exist, discard packet
            VerifyOrExit(mplOffset == 0, error = OT_ERROR_PARSE);

            mplOffset = offset;
            mplLength = option.GetLength();

            VerifyOrExit(mplLength <= sizeof(OptionMpl) - sizeof(OptionHeader), error = OT_ERROR_PARSE);

            if (mplOffset == sizeof(ip6Header) + sizeof(hbh) && hbh.GetLength() == 0)
            {
                // first and only IPv6 Option, remove IPv6 HBH Option header
                remove = true;
            }
            else if (mplOffset + 8 == endOffset)
            {
                // last IPv6 Option, remove last 8 bytes
                remove = true;
            }

            offset += sizeof(option) + option.GetLength();
            break;

        case OptionPad1::kType:
            offset += sizeof(OptionPad1);
            break;

        case OptionPadN::kType:
            offset += sizeof(option) + option.GetLength();
            break;

        default:
            // encountered another option, now just replace MPL Option with PadN
            remove = false;
            offset += sizeof(option) + option.GetLength();
            break;
        }
    }

    // verify that IPv6 Options header is properly formed
    VerifyOrExit(offset == endOffset, error = OT_ERROR_PARSE);

    if (remove)
    {
        // last IPv6 Option, shrink HBH Option header
        uint8_t buf[8];

        offset = endOffset - sizeof(buf);

        while (offset >= sizeof(buf))
        {
            aMessage.Read(offset - sizeof(buf), sizeof(buf), buf);
            aMessage.Write(offset, sizeof(buf), buf);
            offset -= sizeof(buf);
        }

        aMessage.RemoveHeader(sizeof(buf));

        if (mplOffset == sizeof(ip6Header) + sizeof(hbh))
        {
            // remove entire HBH header
            ip6Header.SetNextHeader(hbh.GetNextHeader());
        }
        else
        {
            // update HBH header length
            hbh.SetLength(hbh.GetLength() - 1);
            aMessage.Write(sizeof(ip6Header), sizeof(hbh), &hbh);
        }

        ip6Header.SetPayloadLength(ip6Header.GetPayloadLength() - sizeof(buf));
        aMessage.Write(0, sizeof(ip6Header), &ip6Header);
    }
    else if (mplOffset != 0)
    {
        // replace MPL Option with PadN Option
        OptionPadN padOption;

        padOption.Init(sizeof(OptionHeader) + mplLength);
        aMessage.Write(mplOffset, padOption.GetTotalLength(), &padOption);
    }

exit:
    return error;
}