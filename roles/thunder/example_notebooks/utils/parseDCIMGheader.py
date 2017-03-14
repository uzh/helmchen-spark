import struct
import os
import sys

# adapted from https://github.com/orlandi/hamamatsuOrcaTools/blob/master/DCIMG_opener.py

def main(file_or_bytes):
    is_byte_stream = False
    try:
        is_file = os.path.isfile(file_or_bytes)
    except:
        is_byte_stream = True
        is_file = False
    if is_file:
        with open(file_or_bytes, 'rb') as fid:
            fid.seek(0)
            hdr_bytes = fid.read(232)
    else:
        hdr_bytes = file_or_bytes[:232]
    hdr = parse_header_bytes(hdr_bytes)
    return hdr


# def get_header(fid):
#     hdr_bytes = read_header_bytes(fid)
#     hdr = parse_header_bytes(hdr_bytes)
#     return hdr
#
# def read_header_bytes(self):
#     self.seek(0)
#     # initial metadata block is 232 bytes
#     return self.read(232)


def parse_header_bytes(hdr_bytes):
    header = {}

    bytes_to_skip = 4*from_bytes(hdr_bytes[8:12],byteorder='little')

    curr_index = 8 + bytes_to_skip

    # nframes
    nfrms = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')
    header['nframes'] = nfrms

    # filesize
    curr_index = 48
    header['filesize'] = from_bytes(hdr_bytes[curr_index:curr_index+8],byteorder='little')

    # bytes per pixel
    curr_index = 156
    header['bitdepth'] = 8*from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')

    # footer location
    curr_index = 120
    header['footer_loc'] = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')

    # number of columns (x-size)
    curr_index = 164
    header['xsize_req'] = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')

    # bytes per row
    curr_index = 168
    header['bytes_per_row'] = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')
    #if we requested an image of nx by ny pixels, then DCIMG files
    #for the ORCA flash 4.0 still save the full array in x.
    header['xsize'] = header['bytes_per_row']/2

    # binning
    # this only works because MOSCAM always reads out 2048 pixels per row
    # at least when connected via cameralink. This would fail on USB3 connection
    # and probably for other cameras.
    # TODO: find another way to work out binning
    header['binning'] = int(4096/header['bytes_per_row'])

    # funny entry pair which references footer location
    curr_index = 192
    odd = from_bytes(hdr_bytes[curr_index:curr_index+8],byteorder='little')
    curr_index = 40
    offset = from_bytes(hdr_bytes[curr_index:curr_index+8],byteorder='little')
    header['footer_loc'] = odd+offset

    # number of rows
    curr_index = 172
    header['ysize'] = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')

    # TODO: what about ystart?

    # bytes per image
    curr_index = 176
    header['bytes_per_img'] = from_bytes(hdr_bytes[curr_index:curr_index+4],byteorder='little')

    #if header['bytes_per_img'] != header['bytes_per_row']*header['ysize']:
    #    err_str = "bytes per img ({bytes_per_img}) /= nrows ({ysize}) * bytes_per_row
    # ({bytes_per_row})".format(**header)
    #    raise DcimgError(err_str)

    return header


# There is probably an easier way to do that
def from_bytes (data, byteorder = 'little'):
    if byteorder!='little':
        data = reversed(data)
    num = 0
    for offset, byte in enumerate(data):
        #nb = toBytes(byte)
        nb = struct.unpack('B', byte[0])[0]
        #num += nb[0] << (offset * 8)
        num += nb << (offset * 8)
    return num


if __name__ == '__main__':
    file_or_bytes = sys.argv[1]
    hdr = main(file_or_bytes)
    print hdr
