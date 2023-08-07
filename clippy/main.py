import requests
import argparse
import json
import sys
import os
from rich.console import Console
from rich.markdown import Markdown
import sys

console = Console()


class Clippy:

   def _check(self):
      try:
         requests.get(self.url)
      except:
         raise Exception("Could not connect to {}".format(self.url))

   def __init__(self, url, personality=None, user=None, passwd=None):
      self.url = url

      if (user and not passwd) or (passwd and not user):
         raise Exception("Bot user and password must be set")

      self.user = user
      self.password = passwd

      self._check()
      if personality:
         with open(personality, "r") as f:
            self.personality = f.read()
      else:
         self.personality = """
You are clippy a coding assisant, you are the successor of the clippy from MS Word, and you behave similarly.
You are here to make your best to answer questions from User.
You make structured responses (possibly with subparts with markdown headings) and try to highlight all possibilities while remaining concise.
You use as much markdown as possible in your answers as supported by commonmark.
When outputing code do not forget to put the right language in the MD syntax, for example:

```python
print("hello assistant")
```

Always put code in codeblocks.
Never mention you use markdown just do it!
Never say things such as please note that the above response is just an example and not a real answer.
Do not infer what user would say.


User: Hello!
Clippy: Hello dear user how can I help you ?
User: Give me some examples of native and interpreted languages
Clippy:
# Native

- C : is a native language of reference
- C++ : add object oriented notation to C

## Interpreted

- Python: is a very popular language
- Perl: uses the same VM as python




      """
      self.ctx = [self.personality]

   def userprompt(self):
      console.print("\n[bold magenta]User[/]: ", end="")
      sys.stdout.flush()

   def rewrite_to_md(self, content, lines_to_clear=0):
      md = Markdown(content.replace("Clippy:","**Clippy:** ").replace("Clippy:","**Clippy:** "),
                    justify="left")
      print("\033[{}A\033[J".format(lines_to_clear))
      console.print(md,end='',justify="left")

   def query(self, query, single=False, md=True):
      self.ctx.append("User: {}".format(query))
      ctx = "\n".join(self.ctx)

      session = requests.Session()
      if self.user:
         session.auth = (self.user, self.password)


      resp = session.post("{}/completion".format(self.url), stream=True, json={
                              "stream": True,
                              "n_predict": 400,
                              "temperature": 0.7,
                              "stop" : [ "User:"],
                              # "repeat_last_n": 256,
                              # "repeat_penalty": 1.18,
                              # "top_k": 40,
                              # "top_p": 0.5,
                              # "tfs_z": 1,
                              # "typical_p": 1,
                              # "presence_penalty": 0,
                              # "frequency_penalty": 0,
                              # "mirostat": 0,
                              # "mirostat_tau": 5,
                              # "mirostat_eta": 0.1,
                              "prompt": ctx
                              })

      if resp.status_code != 200:
         raise Exception("Had non 200 response {}".format(resp.status_code))

      Clippyresp = ""

      line_count = 0

      for line in resp.iter_lines():
         if line:
               try:
                  rjs = ":".join(line.decode("utf-8").split(":")[1:])
                  js = json.loads(rjs)
                  r = js["content"]
                  Clippyresp = Clippyresp + r
                  line_count = line_count + len([ x for x in r if x in ['\n','\r']])

                  print(r, end="")
                  sys.stdout.flush()

               except Exception as e:
                  print(e)

      if md:
         self.rewrite_to_md(Clippyresp, line_count)

      self.ctx.append(Clippyresp)
      if not single:
         self.userprompt()


   def handle_command(self, line):
      try:
         if line.startswith("/read"):
            file = line.split(" ")
            if len(file)!=2:
               raise Exception("Bad parameter to /file")
            file = file[1].replace("\n","")
            console.print("[bold blue]Loading {}[/]".format(file))
            with open(file,"r") as f:
               d = f.read()
               print(d)
               return d
         elif line.startswith("/help"):
            print("/read [FILE] : send a file to Clippy")
            print("/help show this help")
      except Exception as e:
         print(e)
         return ""
      return line

   def chat(self,query=None, md=True):
      if query:
         self.query(query, md=md)
      else:
         self.userprompt()
      while a := sys.stdin.readline():
         a = self.handle_command(a)
         self.query(a, md=md)

   def single(self, query, md=True):
      self.query(query, single=True, md=md)


import argparse

def main():
   parser = argparse.ArgumentParser()

   # Define the arguments
   parser.add_argument('--server', '-s', metavar='URL', type=str, help='Server URL (also LLAMA_SERVER from env)', default="http://localhost:8080")
   parser.add_argument('--personality', '-p', metavar='FILE', type=str, help='Personality file')
   parser.add_argument('--interactive', '-i', action='store_true', help='Run the application interactively')
   parser.add_argument('--plain', '-t', action='store_true', help='Do not generate markdown keep plain text')
   parser.add_argument('--user', '-u', type=str, help='HTTP user (both pwd and login can be set from env with LLAMA_HTTP_PWD=login:pwd)', default=None)
   parser.add_argument('--passwd', '-P', type=str, help='HTTP pass', default=None)

   parser.add_argument('text', nargs='*')

   # Parse the arguments
   args = parser.parse_args(sys.argv[1:])

   server = args.server

   env_addr = os.getenv("LLAMA_SERVER")

   if env_addr:
      server = env_addr


   user=args.user
   passwd=args.passwd

   env_pwd = os.getenv("LLAMA_HTTP_PWD")

   if env_pwd:
      a = env_pwd.split(":")
      if len(a) != 2:
         raise Exception("Expected login:pwd had {}".format(env_pwd))
      user = a[0]
      passwd = a[1]


   l = Clippy(server, args.personality, user=user, passwd=passwd)

   use_md = not args.plain

   text = None

   if args.text:
      text = " ".join(args.text)

   if not sys.stdin.isatty():
      if args.interactive:
         raise Exception("Interactive is not compatible with piped output")
      text = text + sys.stdin.read()

   if args.interactive:
      l.chat(text, md=use_md)
   else:
      l.single(text, md=use_md)
