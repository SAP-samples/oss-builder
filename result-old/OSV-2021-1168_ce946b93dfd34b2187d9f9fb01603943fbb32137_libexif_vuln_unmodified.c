mnote_apple_entry_get_value(MnoteAppleEntry *entry, char *v, unsigned int maxlen) {
    ExifLong  vl;
    ExifSLong vsl;
    ExifShort vs;
    ExifSShort vss;
    ExifRational vr;
    ExifSRational vsr;
    size_t size;
    unsigned char *data;

    if (!entry)
        return NULL;

    memset(v, 0, maxlen);
    maxlen--;

    size = entry->size;
    data = entry->data;
    switch (entry->tag) {
    case MNOTE_APPLE_TAG_HDR:
	if (size < 4) return NULL;
	if (entry->format != EXIF_FORMAT_SLONG) return NULL;
	if (entry->components != 1) return NULL;

        vsl = exif_get_slong(data, entry->order);
        snprintf(v, maxlen, "%d", vsl);
        break;
    case MNOTE_APPLE_TAG_IMAGE_UNIQUE_ID:
    case MNOTE_APPLE_TAG_BURST_UUID:
    case MNOTE_APPLE_TAG_MEDIA_GROUP_UUID:
	if (entry->format != EXIF_FORMAT_ASCII) return NULL;
	strncpy (v, (char *) data, MIN (maxlen-1, size));
	v[MIN (maxlen-1, size)] = 0;
        break;
    default:
	switch (entry->format) {
	case EXIF_FORMAT_ASCII:
	    strncpy (v, (char *)data, MIN(maxlen, size));
	    break;
	case EXIF_FORMAT_SHORT: {
	    size_t i, len = 0;

	    for(i=0; i<entry->components; i++) {
		if (size < 2)
		    break;
		if (len > maxlen)
		    break;
		vs = exif_get_short (data, entry->order);
		snprintf (v+len, maxlen-len, "%hu ", vs);
		len = strlen(v);
		data += 2;
		size -= 2;
	    }
	    }
	    break;
	case EXIF_FORMAT_SSHORT: {
	    size_t i, len = 0;
	    for(i=0; i<entry->components; i++) {
		if (size < 2)
		    break;
		if (len > maxlen)
		    break;
		vss = exif_get_sshort (data, entry->order);
		snprintf (v+len, maxlen-len, "%hi ", vss);
		len = strlen(v);
		data += 2;
		size -= 2;
	    }
	}
	break;
        case EXIF_FORMAT_LONG: {
	    size_t i, len = 0;
	    for(i=0; i<entry->components; i++) {
		if (size < 4)
		    break;
		if (len > maxlen)
		    break;
		vl = exif_get_long (data, entry->order);
		snprintf (v+len, maxlen-len, "%lu ", (long unsigned) vl);
		len = strlen(v);
		data += 4;
		size -= 4;
	    }
	    }
	    break;
	case EXIF_FORMAT_SLONG: {
	    size_t i, len = 0;
	    for(i=0; i<entry->components; i++) {
		if (size < 4)
		    break;
		if (len > maxlen)
		    break;
		vsl = exif_get_slong (data, entry->order);
		snprintf (v+len, maxlen-len, "%li ", (long int) vsl);
		len = strlen(v);
		data += 4;
		size -= 4;
	    }
	    }
	    break;
	case EXIF_FORMAT_RATIONAL:
	    vr = exif_get_rational (data, entry->order);
	    if (!vr.denominator) break;
	    snprintf (v, maxlen, "%2.4f", (double) vr.numerator /
					    vr.denominator);
	    break;
	case EXIF_FORMAT_SRATIONAL:
	    vsr = exif_get_srational (data, entry->order);
	    if (!vsr.denominator) break;
	    snprintf (v, maxlen, "%2.4f", (double) vsr.numerator /
		  vsr.denominator);
	    break;
	case EXIF_FORMAT_UNDEFINED:
	default:
	    snprintf (v, maxlen, _("%i bytes unknown data"), entry->size);
	    break;
        }
	break;
     }

     return v;
}