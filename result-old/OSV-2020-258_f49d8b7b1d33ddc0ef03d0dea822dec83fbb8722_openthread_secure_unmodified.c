void MleRouter::SendChildUpdateResponse(Child *                 aChild,
                                        const Ip6::MessageInfo &aMessageInfo,
                                        const uint8_t *         aTlvs,
                                        uint8_t                 aTlvsLength,
                                        const ChallengeTlv &    aChallenge)
{
    otError  error = OT_ERROR_NONE; //?!! enum const OT_ERROR_NONE = 0 of otError
    Message *message;

    VerifyOrExit((message = NewMleMessage()) != NULL, error = OT_ERROR_NO_BUFS); //?!! enum const OT_ERROR_NO_BUFS = 3 of otError
    SuccessOrExit(error = AppendHeader(*message, Header::kCommandChildUpdateResponse)); //?!! enum const kCommandChildUpdateResponse = 14 of Command

    for (int i = 0; i < aTlvsLength; i++)
    {
        switch (aTlvs[i])
        {
        case Tlv::kStatus: //?!! enum const kStatus = 17 of Type
            SuccessOrExit(error = AppendStatus(*message, StatusTlv::kError)); //?!! enum const kError = 1 of Status
            break;

        case Tlv::kAddressRegistration: //?!! enum const kAddressRegistration = 19 of Type
            SuccessOrExit(error = AppendChildAddresses(*message, *aChild));
            break;

        case Tlv::kLeaderData: //?!! enum const kLeaderData = 11 of Type
            SuccessOrExit(error = AppendLeaderData(*message));
            break;

        case Tlv::kMode: //?!! enum const kMode = 1 of Type
            SuccessOrExit(error = AppendMode(*message, aChild->GetDeviceMode()));
            break;

        case Tlv::kNetworkData: //?!! enum const kNetworkData = 12 of Type
            SuccessOrExit(error = AppendNetworkData(*message, !aChild->IsFullNetworkData()));
            SuccessOrExit(error = AppendActiveTimestamp(*message));
            SuccessOrExit(error = AppendPendingTimestamp(*message));
            break;

        case Tlv::kResponse: //?!! enum const kResponse = 4 of Type
            SuccessOrExit(error = AppendResponse(*message, aChallenge.GetChallenge(), aChallenge.GetChallengeLength()));
            break;

        case Tlv::kSourceAddress: //?!! enum const kSourceAddress = 0 of Type
            SuccessOrExit(error = AppendSourceAddress(*message));
            break;

        case Tlv::kTimeout: //?!! enum const kTimeout = 2 of Type
            SuccessOrExit(error = AppendTimeout(*message, aChild->GetTimeout()));
            break;

        case Tlv::kMleFrameCounter: //?!! enum const kMleFrameCounter = 8 of Type
            SuccessOrExit(error = AppendMleFrameCounter(*message));
            break;

        case Tlv::kLinkFrameCounter: //?!! enum const kLinkFrameCounter = 5 of Type
            SuccessOrExit(error = AppendLinkFrameCounter(*message));
            break;
        }
    }

    SuccessOrExit(error = SendMessage(*message, aMessageInfo.GetPeerAddr()));

    if (aChild == NULL)
    {
        LogMleMessage("Send Child Update Response to child", aMessageInfo.GetPeerAddr());
    }
    else
    {
        LogMleMessage("Send Child Update Response to child", aMessageInfo.GetPeerAddr(), aChild->GetRloc16());
    }

exit:

    if (error != OT_ERROR_NONE && message != NULL)
    {
        message->Free();
    }
}