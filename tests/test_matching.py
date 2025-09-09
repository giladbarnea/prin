"""
Sep 9 2025 - known issues:
- [ ] `prin '/tmp/*bar*'` wouldn't match `/tmp/navbar.txt`.
- [ ] `prin github.com/rust-lang/book -l` errors with requests.exceptions.HTTPError: 404 Client Error: Not Found for url: https://api.github.com/repos/rust-lang/book/contents/book?ref=main
"""