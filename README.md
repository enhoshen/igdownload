## examples

```shell
# SESION_ID is the instagram authentication session id

# read from input.txt, each line is a instagram post url and download medias to ./download/
python script.py -l $SESSION_ID -i input.txt -o ./download/
# download story from url to ./download/
python -i script.py -l $SESSION_ID -s <story url> -o ./download/
# store each link saved in the collection "download" into file "links.txt" and
# unsave each saved items. Later use the first example command to download
# the media
python -i script.py -l $SESION_ID -c "download" --download_links "links.txt" --unsave
```

## requirements

- `instagrapi`
