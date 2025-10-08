# Week 3: Creating your Agent, part 2

Hey everyone, welcome to week 3 of the spotify agent project!

This week we'll be setting up our MCP server that will let our agent connect to and use Spotify.

## MCP Recap

Its been a while since week one, so in case you forgot, MCP is an open source framework that enables LLMs to use external tools (such as Spotify). I'll attach a link to the same explanation video from before.

https://www.youtube.com/watch?v=FLpS7OfD5-s


An MCP server, as mentioned in the video, is just where all of the different tools and API endpoints live that our model can then call.

The cool thing about MCP servers is that we actually don't always need to create them ourselves. Many companies provide official MCP servers for access to their services; spotify hasn't gotten around to that yet. Instead, we'll be using a third party server, created by some kind developers, that will bring MCP functionality to our agent. 

## Git Cloning the MCP Server

In the terminal of your code editor, type *cd ..* to back out to the parent directory of spotify agent folder. While in this directory, type *git clone https://github.com/marcelmarais/spotify-mcp-server.git* 

Feel free to dig through the source code of this MCP server btw, its all publically available. I've attached a link to the github here

https://github.com/marcelmarais/spotify-mcp-server


You have now cloned the MCP server to your local computer. You might notice that the MCP server is written in JavaScript, which you do not need to know for this project! MCP is language agnostic, so we can integrate an MCP server written in JS with an agent written in Python. We will, however, need to install an application called Node.js, so we can actually run the javascript code on our computer.

## Installing Node.js

### Windows
1. Visit the official Node.js website at https://nodejs.org/

2. Download the Windows Installer (.msi) file - choose either the LTS (Long Term Support)  version for stability or the Current version for the latest features

3. Run the downloaded installer

4. Follow the installation wizard:

    - Accept the license agreement
    - Choose the installation location (default is usually fine)
    - Select components to install (default settings include npm)

5. Click "Install" and wait for the process to complete


6. Verify the installation by opening Terminal and typing:
*node --version*
*npm --version*

7. You may have to restart your terminal or your computer for this to work.

### MacOS
1. Install Homebrew if you haven't already from https://brew.sh/

2. Open Terminal and run
*brew install node*

3. Verify the installation by opening Terminal and typing:
*node --version*
*npm --version*

4. You may have to restart your terminal or your computer for this to work.

## Setting up Spotify credentials within the MCP server

Now, open up a new window of your code editor initialized with the mcp server we just cloned. Follow the setup tutorial in the README.md file (found at the bottom). When posting over credentials to *spotify-config.json*, make sure to to use the same credentials from your *.env* file and also make sure to update the redirect URI to what we have saved in *.env* (it's something else by default.)

Cool, you've now set up your mcp server for later use.


## Adding a function to kill port proccesses
Lastly, we'll add one more bonus function to our code that we'll execute after we've validated our API credentials. If you recall, we added a 'redirect_uri' to our *.env* file. Essentially, the spotify api is running a server at this 'redirect_uri' that authenticates the requests we make. However, if we try to use the same credentials again within the same code, we'll get an error. This is because that location on our computer, known as a port, is already being used to run a server from the last time we needed to authenticate. Specifically, the server is being run on port 8090, which you can see in the URL: "http://127.0.0.1:8090/callback".

So after we finish authenticating our credentials, we'll run a function that will kill all processes running on that port, so that we can use the same port again later.

Copy the following function into your agent_script.py file based on your OS

### MacOS/Linux
Add the following to the imports sectin of your code

*import subprocess*

Then copy this function later on

```
def kill_processes_on_port(port):
    """Kill all processes running on the specified port"""
    try:
        # Find processes using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"Found processes on port {port}: {pids}")
            
            # Kill each process
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(['kill', '-9', pid], check=True)
                        print(f"Killed process {pid} on port {port}")
                    except subprocess.CalledProcessError:
                        print(f"Failed to kill process {pid}")
        else:
            print(f"No processes found on port {port}")
            
    except FileNotFoundError:
        print("lsof command not found, trying alternative method...")
        try:
            # Alternative method using netstat and kill
            result = subprocess.run(['netstat', '-tulpn'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) > 6 and '/' in parts[6]:
                            pid = parts[6].split('/')[0]
                            try:
                                subprocess.run(['kill', '-9', pid], check=True)
                                print(f"Killed process {pid} on port {port}")
                            except subprocess.CalledProcessError:
                                print(f"Failed to kill process {pid}")
        except Exception as e:
            print(f"Error killing processes on port {port}: {e}")
```

### Windows

Add the following to the imports section of your code

*import subprocess*

Then copy this function later in your code

```
def kill_processes_on_port(port):
    """Kill processes on Windows"""
    try:
        # Find processes using the port
        result = subprocess.run(['netstat', '-ano'], 
                              capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            pids_to_kill = []
            
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]  # Last column is PID
                        if pid.isdigit():
                            pids_to_kill.append(pid)
            
            if pids_to_kill:
                print(f"Found processes on port {port}: {pids_to_kill}")
                for pid in pids_to_kill:
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], 
                                     check=True, capture_output=True)
                        print(f"Killed process {pid} on port {port}")
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to kill process {pid}: {e}")
            else:
                print(f"No processes found on port {port}")
        else:
            print(f"Failed to run netstat: {result.stderr}")
            
    except Exception as e:
        print(f"Error killing processes on port {port}: {e}")

```

Now, add this function for port 8090 in your main function, after you validate your spotify and groq credentials. 

## Conclusion

Thanks for joining us this week! Next week, we'll begin defining our agent behavior with LangGraph and start making some AI-generated playlists.




