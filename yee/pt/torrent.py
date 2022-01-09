from yee.pt.torrent_search import TorrentSearch
import bencoder, hashlib

find_torrent_by_episodes = TorrentSearch.find_torrent_by_episodes
check_ep_in_torrent = TorrentSearch.check_ep_in_torrent


def info_hash(torrent_file):
    objTorrentFile = open(torrent_file, "rb")
    decodedDict = bencoder.decode(objTorrentFile.read())
    info_hash = hashlib.sha1(bencoder.encode(decodedDict[b"info"])).hexdigest()
    return info_hash
