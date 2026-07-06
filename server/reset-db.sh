#!/bin/bash
echo "Deleting AnxioSense database..."
rm -f data/anxiosense.db data/anxiosense.db-shm data/anxiosense.db-wal
echo "Done! Database will be recreated fresh when you run: npm run dev"
