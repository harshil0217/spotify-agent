# Week 2: Creating your Agent, Part 1

Hey! Welcome back and thanks for joining us for week 2 of the Spotify Agent project. I hope last week went well for you and you were able to set up your development enviornment/credentials without too many hiccups. This week we'll start writing the script for our LangGraph-based Spotify Agent. After this week and the next, you'll have an agent you can interact with from the terminal.

This week, we'll populate an env file for our API keys and credentials and validate that those credentials are actually working. Next week, we'll set up the framework for our agent and begin experimenting with it.

## Setting up our env file

In the root of your directory that we set up last week, add a file called ".env" (note: env is different from venv. venv contains our python version and all of the external libraries we'll be using, env contains our "secrets". We want to ensure both are not pushed to GitHub). We'll place all of our credentials in this file so they can be stored securely.

Copy the following into your .env file

SPOTIFY_CLIENT_ID = YOUR SPOTIFY CLIENT ID
SPOTIFY_CLIENT_SECRET= YOUR SPOTIFY CLIENT SECRET
SPOTIFY_REDIRECT_URI= YOUR SPOTIFY REDIRECT URI
GROQ_API_KEY= YOUR GROQ API KEY

Of course, replacing the values for the variables with the credentials you created last week.

Now, ensure that .env is specified within your .gitignore file, and if it is, create a new file called "agent_script.py". Commit your changes, and push to GitHub.

To make sure everything has gone according to plan, check your remote repository (the code on the github website) to ensure that neither the env file or the venv file are there. You should just see the agent_script.py file, the .gitignore, and possibly a ReadMe if you chose to create one. 

## Validating our credentials

Now that we have our credentials within our .env file, let's write some quick checks to ensure that our credentials are actually valid and working.

Begin by installing the following libraries using your terminal

uv pip install requests
uv pip install python-dotenv

The requests library will allow us to communicate with external servies (i.e. the Spotify and Groq APIs). The 'python-dotenv' library will enable us to load in the variables defined in .env as enviornment variables that we can use in our script

By the way, if you aren't aware, pip is the standard commmand used to install external python modules. We are prefacing it with "uv" since we used uv to create our virtual enviornment.

Then import the following libraries at the top of your script

import os
import requests
from dotenv import load_dotenv

os is default to python, so you don't need to worry about pip installing it.

Now, lets actually get to writing some code.

In a new line write:

load_dotenv()

This function will load in all of the variables from .env.

Next, copy and paste the following function into your file.

    def check_spotify_credentials():
        """
        Check if Spotify API credentials are valid by attempting to get an access token.
        Returns True if valid, False otherwise.
        """
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
        
        # Check if credentials exist
        if not all([client_id, client_secret, redirect_uri]):
            print("❌ Missing Spotify credentials in .env file")
            return False
        
        # Test credentials by requesting a client credentials token
        auth_url = "https://accounts.spotify.com/api/token"
        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        try:
            response = requests.post(auth_url, headers=auth_headers, data=auth_data)
            if response.status_code == 200:
                print("✅ Spotify credentials are valid")
                return True
            else:
                print(f"❌ Spotify credentials invalid. Status: {response.status_code}")
                print(f"Response: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ Error checking Spotify credentials: {e}")
            return False

    
This function will ensure the spotify credentials in our .env file are legitimate and will work later on. Take some time to go through this code line by line and understand how it's working. Specifically, pay attention to how information is being passed to the requests module and how that module is being used to validate our env credentials.

(It is a good idea to be familiar with the common http status codes, I've attached an educational resource here: https://www.geeksforgeeks.org/blogs 10-most-common-http-status-codes/)

Now create a similar function for checking our groq credentials and title it "check_groq_credentials()". 

Finally, lets define our main function. 

    def main():
        print("Checking API credentials...\n")
        
        spotify_valid = check_spotify_credentials()
        groq_valid = check_groq_credentials()
        
        print(f"\nCredentials Summary:")
        print(f"Spotify: {'✅ Valid' if spotify_valid else '❌ Invalid'}")
        print(f"Groq: {'✅ Valid' if groq_valid else '❌ Invalid'}")
        
        if spotify_valid and groq_valid:
            print("\n🎉 All credentials are working!")
        else:
            print("\n⚠️  Please fix invalid credentials before proceeding.")

and add 

    if __name__ == "__main__":
        main()

at the very end of our file. This will ensure that our main function will execute when we run our file.

If all is well, you should run into no issues. Please do not hesitate to reach out in the event that you do.

## Asynchronous Functions
Before we begin building our agent next week, it is a good idea to familiarize yourself with asynchronous programming in python, if you are not already. Many aspects of our agent will involving sending and receiving information to external services and servers running elsewhere on our computer; this will be much easier to accomplish using asynchronous programming. I've attached the following resources that will help you understand how this works:

https://www.youtube.com/watch?v=Qb9s3UiMSTA
https://realpython.com/async-io-python/


## Conclusion

Thanks for joining us again this week! Don't worry, next week we'll get into the nitty-gritty details of actually building our agent. See you then!






