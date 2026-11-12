Use the truncate command from GNU coreutils:

- Truncate to zero length (empty the file):
  truncate -s 0 filename.txt

Other handy variants:
- Truncate to a specific size (e.g., 1K, 10M):
  truncate -s 1K filename.txt
  truncate -s 10M filename.txt

- Empty a file using shell redirection (works in most shells):
  :> filename.txt
  > filename.txt

- Truncate multiple files at once:
  truncate -s 0 file1.txt file2.log

Note: If you don’t want to create the file if it doesn’t exist, add -c (no-create) like:
truncate -s 0 -c filename.txt