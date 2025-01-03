exif_mnote_data_apple_load(ExifMnoteData *md, const unsigned char *buf, unsigned int buf_size) {
    ExifMnoteDataApple *d = (ExifMnoteDataApple *) md;
    unsigned int tcount, i;
    unsigned int dsize;
    unsigned int ofs, dofs;

    /*printf("%s\n", __FUNCTION__);*/

    if (!d || !buf || (buf_size < 6 + 16)) {
        exif_log(md->log, EXIF_LOG_CODE_CORRUPT_DATA, //?!! enum const EXIF_LOG_CODE_CORRUPT_DATA = 3
                 "ExifMnoteDataApple", "Short MakerNote");
        return;
    }

    /* Start of interesting data */
    ofs = d->offset + 6;
    if (ofs > buf_size - 16) {
        exif_log(md->log, EXIF_LOG_CODE_CORRUPT_DATA,
                 "ExifMnoteDataApple", "Short MakerNote");
        return;
    }

    if ((buf[ofs + 12] == 'M') && (buf[ofs + 13] == 'M')) {
        d->order = EXIF_BYTE_ORDER_MOTOROLA; //?!! enum const EXIF_BYTE_ORDER_MOTOROLA = 0
    } else if ((buf[ofs + 12] == 'I') && (buf[ofs + 13] == 'I')) {
        d->order = EXIF_BYTE_ORDER_INTEL; //?!! enum const EXIF_BYTE_ORDER_INTEL = 1
    } else {
        exif_log(md->log, EXIF_LOG_CODE_CORRUPT_DATA,
                "ExifMnoteDataApple", "Unrecognized byte order");
        /*printf("%s(%d)\n", __FUNCTION__, __LINE__);*/
        return;
    }

    tcount = (unsigned int) exif_get_short(buf + ofs + 14, d->order);

    /* Sanity check the offset */
    if (buf_size < 6 + 16 + tcount * 6 + 4) {
        exif_log(md->log, EXIF_LOG_CODE_CORRUPT_DATA,
                 "ExifMnoteDataApple", "Short MakerNote");
        /*printf("%s(%d)\n", __FUNCTION__, __LINE__);*/
        return;
    }

    /* printf("%s(%d): total %d tags\n", __FUNCTION__, __LINE__, tcount); */

    ofs += 16;

    exif_mnote_data_apple_free(md);

    /* Reserve enough space for all the possible MakerNote tags */
    d->entries = exif_mem_alloc(md->mem, sizeof(MnoteAppleEntry) * tcount);
    if (!d->entries) {
        EXIF_LOG_NO_MEMORY(md->log, "ExifMnoteApple", sizeof(MnoteAppleEntry) * tcount); //?!! enum const EXIF_LOG_CODE_NO_MEMORY = 2
        /*printf("%s(%d)\n", __FUNCTION__, __LINE__);*/
        return;
    }

    for (i = 0; i < tcount; i++) {
        d->entries[i].tag = exif_get_short(buf + ofs, d->order);
        d->entries[i].format = exif_get_short(buf + ofs + 2, d->order);
        d->entries[i].components = exif_get_long(buf + ofs + 4, d->order);
        d->entries[i].order = d->order;
        dsize = exif_format_get_size(d->entries[i].format) * d->entries[i].components;
	if (dsize > 65536) {
		/* Corrupt data: EXIF data size is limited to the
		 * maximum size of a JPEG segment (64 kb).
		 */
		continue;
	}
        if (dsize > 4) {
            dofs = d->offset + exif_get_long(buf + ofs + 8, d->order);
        } else {
            dofs = ofs + 8;
        }
        ofs += 12;
        d->entries[i].data = exif_mem_alloc(md->mem, dsize);
        if (!d->entries[i].data) {
            EXIF_LOG_NO_MEMORY(md->log, "ExifMnoteApple", dsize);
            continue;
        }
	if (dofs + dsize > buf_size) {
		exif_log (md->log, EXIF_LOG_CODE_CORRUPT_DATA,
                                  "ExifMnoteApplet", "Tag size overflow detected (%u vs size %u)", dofs + dsize, buf_size);
		continue;
	}
        memcpy(d->entries[i].data, buf + dofs, dsize);
        d->entries[i].size = dsize;
    }
    d->count = tcount;

    return;
}