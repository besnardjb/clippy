import requests
import argparse
import json
import sys
import os
from rich.console import Console
from rich.markdown import Markdown
import sys
import subprocess
import re

console = Console()


class Llama:


   def _links2(self, url):
      return subprocess.check_output(["links2", "-dump", url]).decode()

   def _check(self):
      try:
         requests.get(self.url)
      except:
         raise Exception("Could not connect to {}".format(self.url))

   def __init__(self, url, personality=None, user=None, passwd=None):
      self.url = url

      if (user and not passwd) or (passwd and not user):
         raise Exception("Bot user and password must be set")

      self.session = requests.Session()
      if user:
         self.session.auth = (user, passwd)

      self.reman = r'\(MAN (\s+)\)'
      self.reopen = r'\(OPEN\s+(https?://[^\s/$.?#].[^\s]*)\)'
      self.reurl = r'\(GET\s+(https?://[^\s/$.?#].[^\s]*)\)'
      self.line_count = 0

      self._check()
      if personality:
         with open(personality, "r") as f:
            self.personality = f.read()
      else:
         self.personality = """
# Identity

You are llama a resource aggregator and coding assistant.
You help the user searching information on the Internet.

# Capabilities

## The GET Command

To do so you can ask 'system' to issue HTTP requests for you
by doing (GET URL). You always fetch information first using the command syntax below.

System will respond with the content of the URL in HTML, you will only consider the content and not the code.

As such feel free to send queries to online services and API such as Wikipedia, favor services with text content as you can only process text.
No queries will be made unless you write the command.

You can then use keys from this JSON to search the actual content on wikipedia:
(GET https://en.wikipedia.org/wiki/Python (programming language))
System: content of the Python wikipedia page [...]

Systematically do GET requests first to enrich information. Always put (GET URL) on a single line and wait for system's response.
When parsing a system response do not react to the code but only to the content of the page.

## The OPEN Command

Another command is (OPEN URL) with this command you directly show the page to user:, avoiding to explain. You can use it for example to open google maps or other visual services.

(OPEN http://google.com)

will open google.com to the user, if it is the response he needed. It is a very good way to answer user's question to directly open a page if you cannot provide the answer directly.

# General guidelines

Always focus on the content and answering the user questions, not commenting the code.
As google maps is visual always open is to the user with OPEN while pasing the correct parameters.
When you don't know try a yahoo search and extract links.

# Chat with the USER and System

User: can you open google ?
Llama: (OPEN http://google.com)
User: Tell me more about Brest
Llama: Let me look on Wikipedia to refresh my mind ... (GET http://en.wikipedia.com/wiki/Brest_France)
System: [CONTENT of the BREST page]
Lllama: Brest is a city in Brittany ...
      """

      self.ctx = [self.personality]

   def userprompt(self):
      console.print("\n[bold magenta]User[/]: ", end="")
      sys.stdout.flush()

   def rewrite_to_md(self, content, lines_to_clear=0):
      md = Markdown(content.replace("Llama:","**Llama:** ").replace("llama:","**llama:** "),
                    justify="left")
      print("\033[{}A\033[J".format(lines_to_clear))
      console.print(md,end='',justify="left")

   def parse_each_line(self, linebuff, md=False):
      if "\n" in linebuff:
         m = re.findall(self.reurl, linebuff)
         if m:
            for match in m:
               print(f"Looking for {match} on the web ...")
               self.line_count = self.line_count + 1
               ret = self._links2(match)
               ret_clean = self.blocking_query("""
You are an assistant processing HTML pages for the user summarizing valuable informations from it.
Your name is Llama.

User: Hello how are you ?
Llama: I'm fine what can I do for you ?
User: Can you clean the content of this page to only return the content : \n\n""" + ret)
               print(ret_clean)
               self.query(ret_clean, single=True, md=md, issystem=True)
         m = re.findall(self.reopen, linebuff)
         if m:
            for match in m:
               print(f"Opening for {match} on the web ...")
               self.line_count = self.line_count + 1
               subprocess.call(["xdg-open", match])
         return ""
      return linebuff


   def blocking_query(self, query):
      resp = self.session.post("{}/completion".format(self.url), stream=True, json={
                        "stream": False,
                        "n_predict": 400,
                        "temperature": 0.7,
                        "stop" : [ "User:", "System"],
                        # "repeat_last_n": 256,
                        # "repeat_penalty": 1.18,
                        # "top_k": 40,
                        # "top_p": 0.5,
                        # "tfs_z": 1,
                        # "typical_p": 1,
                        # "presence_penalty": 0,
                        # "frequency_penalty": 0,
                        "mirostat": 2,
                        "mirostat_tau": 5,
                        "mirostat_eta": 0.1,
                        "prompt": query
                        })

      if resp.status_code != 200:
         print(resp.text)
         raise Exception("Had {} response: {}".format(resp.status_code, resp.reason))

      data = resp.json()
      return data["content"]


   def query(self, query, single=False, md=True, issystem=False):
      if issystem:
         self.ctx.append("System: {}".format(query))
      else:
         self.ctx.append("User: {}".format(query))

      ctx = "\n".join(self.ctx)

      resp = self.session.post("{}/completion".format(self.url), stream=True, json={
                              "stream": True,
                              "n_predict": 400,
                              "temperature": 0.7,
                              "stop" : [ "User:", "System"],
                              # "repeat_last_n": 256,
                              # "repeat_penalty": 1.18,
                              # "top_k": 40,
                              # "top_p": 0.5,
                              # "tfs_z": 1,
                              # "typical_p": 1,
                              # "presence_penalty": 0,
                              # "frequency_penalty": 0,
                              "mirostat": 2,
                              "mirostat_tau": 5,
                              "mirostat_eta": 0.1,
                              "prompt": ctx
                              })

      if resp.status_code != 200:
         print(resp.text)
         raise Exception("Had {} response: {}".format(resp.status_code, resp.reason))

      llamaresp = ""


      linebuff = ""


      for line in resp.iter_lines():
         if line:
               try:
                  rjs = ":".join(line.decode("utf-8").split(":")[1:])
                  js = json.loads(rjs)
                  r = js["content"]
                  llamaresp = llamaresp + r
                  self.line_count = self.line_count + len([ x for x in r if x in ['\n','\r']])

                  linebuff = linebuff + r
                  linebuff = self.parse_each_line(linebuff, md=md)


                  print(r, end="")
                  sys.stdout.flush()

               except Exception as e:
                  print(e)
                  raise e

      linebuff += "\n"
      linebuff = self.parse_each_line(linebuff, md=md)

      if md:
         self.rewrite_to_md(llamaresp, self.line_count)

      self.ctx.append(llamaresp)
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
            print("/read [FILE] : send a file to llama")
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


   l = Llama(server, args.personality, user=user, passwd=passwd)

   use_md = not args.plain

   text = ""

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