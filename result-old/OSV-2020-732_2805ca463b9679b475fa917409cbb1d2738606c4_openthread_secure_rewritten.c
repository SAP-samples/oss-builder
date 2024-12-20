void Leader::HandlePetition(Coap::Message &aMessage, const Ip6::MessageInfo &aMessageInfo)
{
    OT_UNUSED_VARIABLE(aMessageInfo);

    CommissioningData data;
    CommissionerIdTlv commissionerId;
    StateTlv::State   state = StateTlv::kReject;

    otLogInfoMeshCoP("received petition");

    VerifyOrExit(GetNetif().GetMle().IsRoutingLocator(aMessageInfo.GetPeerAddr()));
    SuccessOrExit(Tlv::GetTlv(aMessage, Tlv::kCommissionerId, sizeof(commissionerId), commissionerId));
    VerifyOrExit(commissionerId.IsValid());

    if (mTimer.IsRunning())
    {
        VerifyOrExit((commissionerId.GetLength() == mCommissionerId.GetLength()) &&
                     (!strncmp(commissionerId.GetCommissionerId(), mCommissionerId.GetCommissionerId(),
                               commissionerId.GetLength())));

        ResignCommissioner();
    }

    data.mBorderAgentLocator.Init();
    data.mBorderAgentLocator.SetBorderAgentLocator(HostSwap16(aMessageInfo.GetPeerAddr().mFields.m16[7]));

    data.mCommissionerSessionId.Init();
    data.mCommissionerSessionId.SetCommissionerSessionId(++mSessionId);

    data.mSteeringData.Init();
    data.mSteeringData.SetLength(1);
    data.mSteeringData.Clear();

    SuccessOrExit(
        GetNetif().GetNetworkDataLeader().SetCommissioningData(reinterpret_cast<uint8_t *>(&data), data.GetLength()));

    mCommissionerId = commissionerId;

    state = StateTlv::kAccept;
    mTimer.Start(TimerMilli::SecToMsec(kTimeoutLeaderPetition));

exit:
    SendPetitionResponse(aMessage, aMessageInfo, state);
}