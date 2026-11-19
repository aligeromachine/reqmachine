
import time
from reqmachine import HttpClient, http_client, http_get

class Timer:
    def __init__(self, name=""):
        self.name = name
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    def __exit__(self, *exc):
        print(f"{self.name}: {time.perf_counter() - self.start:.4f} c")

@http_client
def fetch_posts(client: HttpClient):
    respo = client.get("https://jsonplaceholder.typicode.com/users")
    print(respo)
    respo = client.get("https://jsonplaceholder.typicode.com/posts")
    print(respo)

def main():

    respo = http_get("https://jsonplaceholder.typicode.com//users")
    print(respo)

    respo = http_get("https://jsonplaceholder.typicode.com/posts")
    print(respo)


if __name__ == "__main__":
    with Timer('fetch_posts') as _:
        fetch_posts()
