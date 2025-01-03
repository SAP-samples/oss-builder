void Leader::HandleCommissioningSet(Coap::Message &aMessage, const Ip6::MessageInfo &aMessageInfo)
{
    uint16_t                 offset = aMessage.GetOffset();
    uint16_t                 length = aMessage.GetLength() - aMessage.GetOffset();
    uint8_t                  tlvs[NetworkData::kMaxSize];
    MeshCoP::StateTlv::State state        = MeshCoP::StateTlv::kReject;
    bool                     hasSessionId = false;
    bool                     hasValidTlv  = false;
    uint16_t                 sessionId    = 0;

    MeshCoP::Tlv *cur;
    MeshCoP::Tlv *end;

    VerifyOrExit(length <= sizeof(tlvs));
    VerifyOrExit(Get<Mle::MleRouter>().GetRole() == OT_DEVICE_ROLE_LEADER);

    aMessage.Read(offset, length, tlvs);

    // Session Id and Border Router Locator MUST NOT be set, but accept including unexpected or
    // unknown TLV as long as there is at least one valid TLV.
    cur = reinterpret_cast<MeshCoP::Tlv *>(tlvs);
    end = reinterpret_cast<MeshCoP::Tlv *>(tlvs + length);

    while (cur < end)
    {
        MeshCoP::Tlv::Type type;

        VerifyOrExit((cur + 1) <= end && cur->GetNext() <= end);

        type = cur->GetType();

        if (type == MeshCoP::Tlv::kJoinerUdpPort || type == MeshCoP::Tlv::kSteeringData)
        {
            hasValidTlv = true;
        }
        else if (type == MeshCoP::Tlv::kBorderAgentLocator)
        {
            ExitNow();
        }
        else if (type == MeshCoP::Tlv::kCommissionerSessionId)
        {
            MeshCoP::CommissionerSessionIdTlv *tlv = static_cast<MeshCoP::CommissionerSessionIdTlv *>(cur);

            VerifyOrExit(tlv->IsValid());
            sessionId    = tlv->GetCommissionerSessionId();
            hasSessionId = true;
        }
        else
        {
            // do nothing for unexpected or unknown TLV
        }

        cur = cur->GetNext();
    }

    // verify whether or not commissioner session id TLV is included
    VerifyOrExit(hasSessionId);

    // verify whether or not MGMT_COMM_SET.req includes at least one valid TLV
    VerifyOrExit(hasValidTlv);

    // Find Commissioning Data TLV
    for (NetworkDataTlv *netDataTlv = reinterpret_cast<NetworkDataTlv *>(mTlvs);
         netDataTlv < reinterpret_cast<NetworkDataTlv *>(mTlvs + mLength); netDataTlv = netDataTlv->GetNext())
    {
        if (netDataTlv->GetType() == NetworkDataTlv::kTypeCommissioningData)
        {
            // Iterate over MeshCoP TLVs and extract desired data
            for (cur = reinterpret_cast<MeshCoP::Tlv *>(netDataTlv->GetValue());
                 cur < reinterpret_cast<MeshCoP::Tlv *>(netDataTlv->GetValue() + netDataTlv->GetLength());
                 cur = cur->GetNext())
            {
                if (cur->GetType() == MeshCoP::Tlv::kCommissionerSessionId)
                {
                    VerifyOrExit(sessionId ==
                                 static_cast<MeshCoP::CommissionerSessionIdTlv *>(cur)->GetCommissionerSessionId());
                }
                else if (cur->GetType() == MeshCoP::Tlv::kBorderAgentLocator)
                {
                    VerifyOrExit(length + cur->GetSize() <= sizeof(tlvs));
                    memcpy(tlvs + length, reinterpret_cast<uint8_t *>(cur), cur->GetSize());
                    length += cur->GetSize();
                }
            }
        }
    }

    SetCommissioningData(tlvs, static_cast<uint8_t>(length));

    state = MeshCoP::StateTlv::kAccept;

exit:

    if (Get<Mle::MleRouter>().GetRole() == OT_DEVICE_ROLE_LEADER)
    {
        SendCommissioningSetResponse(aMessage, aMessageInfo, state);
    }
}