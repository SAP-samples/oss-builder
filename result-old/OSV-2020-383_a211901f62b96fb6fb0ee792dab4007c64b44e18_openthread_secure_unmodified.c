bool Leader::IsStableUpdated(uint8_t *aTlvs, uint8_t aTlvsLength, uint8_t *aTlvsBase, uint8_t aTlvsBaseLength)
{
    bool            rval = false;
    NetworkDataTlv *cur  = reinterpret_cast<NetworkDataTlv *>(aTlvs);
    NetworkDataTlv *end  = reinterpret_cast<NetworkDataTlv *>(aTlvs + aTlvsLength);
#if OPENTHREAD_ENABLE_SERVICE
    ServiceTlv *service;
#endif

    while (cur < end)
    {
        VerifyOrExit((cur + 1) <= end && cur->GetNext() <= end);

        switch (cur->GetType())
        {
        case NetworkDataTlv::kTypePrefix:
        {
            PrefixTlv *      prefix       = static_cast<PrefixTlv *>(cur);
            ContextTlv *     context      = FindContext(*prefix);
            BorderRouterTlv *borderRouter = FindBorderRouter(*prefix, true);
            HasRouteTlv *    hasRoute     = FindHasRoute(*prefix, true);

            if (cur->IsStable() && (!context || borderRouter))
            {
                PrefixTlv *prefixBase =
                    FindPrefix(prefix->GetPrefix(), prefix->GetPrefixLength(), aTlvsBase, aTlvsBaseLength);

                if (!prefixBase)
                {
                    ExitNow(rval = true);
                }

                if (borderRouter)
                {
                    BorderRouterTlv *borderRouterBase = FindBorderRouter(*prefixBase, true);

                    if (!borderRouterBase || (borderRouter->GetLength() != borderRouterBase->GetLength()) ||
                        (memcmp(borderRouter, borderRouterBase, borderRouter->GetLength()) != 0))
                    {
                        ExitNow(rval = true);
                    }
                }

                if (hasRoute)
                {
                    HasRouteTlv *hasRouteBase = FindHasRoute(*prefixBase, true);

                    if (!hasRouteBase || (hasRoute->GetLength() != hasRouteBase->GetLength()) ||
                        (memcmp(hasRoute, hasRouteBase, hasRoute->GetLength()) != 0))
                    {
                        ExitNow(rval = true);
                    }
                }
            }

            break;
        }

#if OPENTHREAD_ENABLE_SERVICE

        case NetworkDataTlv::kTypeService:
            service = static_cast<ServiceTlv *>(cur);

            if (cur->IsStable())
            {
                NetworkDataTlv *curInner;
                NetworkDataTlv *endInner;

                ServiceTlv *serviceBase = FindService(service->GetEnterpriseNumber(), service->GetServiceData(),
                                                      service->GetServiceDataLength(), aTlvsBase, aTlvsBaseLength);

                if (!serviceBase || !serviceBase->IsStable())
                {
                    ExitNow(rval = true);
                }

                curInner = service->GetSubTlvs();
                endInner = service->GetNext();

                while (curInner < endInner)
                {
                    if (curInner->IsStable())
                    {
                        switch (curInner->GetType())
                        {
                        case NetworkDataTlv::kTypeServer:
                        {
                            bool       foundInBase = false;
                            ServerTlv *server      = static_cast<ServerTlv *>(curInner);

                            NetworkDataTlv *curServerBase = serviceBase->GetSubTlvs();
                            NetworkDataTlv *endServerBase = serviceBase->GetNext();

                            while (curServerBase <= endServerBase)
                            {
                                ServerTlv *serverBase = static_cast<ServerTlv *>(curServerBase);

                                VerifyOrExit((curServerBase + 1) <= endServerBase && curServerBase->GetNext() <= end);

                                if (curServerBase->IsStable() && (server->GetServer16() == serverBase->GetServer16()) &&
                                    (server->GetServerDataLength() == serverBase->GetServerDataLength()) &&
                                    (memcmp(server->GetServerData(), serverBase->GetServerData(),
                                            server->GetServerDataLength()) == 0))
                                {
                                    foundInBase = true;
                                    break;
                                }

                                curServerBase = curServerBase->GetNext();
                            }

                            if (!foundInBase)
                            {
                                ExitNow(rval = true);
                            }

                            break;
                        }

                        default:
                            break;
                        }
                    }

                    curInner = curInner->GetNext();
                }
            }

            break;
#endif

        default:
            break;
        }

        cur = cur->GetNext();
    }

exit:
    return rval;
}