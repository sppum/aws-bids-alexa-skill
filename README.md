# Beta access
https://developer.amazon.com/docs/custom-skills/skills-beta-testing-for-alexa-skills.html

# OAuth
1. Create a new 'Login with Amazon Security Profile'
    - Copy the Client ID & Client Secret
2. Configure the skill to use it
    - Developer console > Skill > Account Linking
        - Authorization URL: https://www.amazon.com/ap/oa/?redirect_url= +
          redirect
          e.g. https://www.amazon.com/ap/oa/?redirect_url=https://layla.amazon.com/api/skill/link/M2BQABO2LPRHIO
        - Client ID: Client ID
        - Client Secret: Client Secret
        - Client Authentication Scheme: HTTP Basic
        - Scope: profile
        - Access Token URI: https://api.amazon.com/auth/o2/token
        - Privacy Policy URL: I just used the AWS one...
    - Note the 3 Redirect URLs (layla seems to be the EU one)
3. Link Login with Amazon back to the skill
    - Developer console > Apps & Services > Login with Amazon > Web Settings
        - Allowed Return URLs: the 3 from the Alexa Skills Kit
4. Login to Amazon from the skill, OAUTH dance...

# Testing
If you want to use the Alexa Skills Kit (ask) then the following could be
useful.

1. Make sure you have installed ASK per the instructions below
    - https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html
2. If you haven't used ASK on this project before:
    - 'ask init'
        - Create the profile if needed, select one you already have if desired
    - Once the OAuth dance is done choose the Vendor ID where the skill is
      installed
3. Get the ID for the skill you want to test:
    - 'ask api list' | jq '.skills[] | select(.nameByLocale["en-GB"] | test("bid support")) .skillId'
        - (this errors a bit, needs fixing)
4. Now use 'ask simulate', for example:
    - 'ask simulate -l en-GB -s amzn1.ask.skill.dc7737f5-ba27-49fe-95d6-63695240beed -t "ask sales support to email me the DUNS number for amazon"'

More here:
    - https://github.com/alexa/skill-sample-nodejs-test-automation/blob/master/labs/lab03.md

# Things
Manually add email to SES; this is checked by verifyEmail and is needed for the function to work
    - create a function to subscribe an address if it isn't present?

If you want to use sam local to test, then:
    - Use the following flags to 'sam local'
        '--env-vars env.json --docker-network localstack'
    - Bring the localstack container up:
        'docker-compose -f localstack-compose.yml up'
    - You'll have needed to build locally too:
        - Add 'build/' to the end of CodeUri sections in samTemplate.yaml
        - While the build sub-directories are ignored by git, make sure you
          clean before you build
        - 'for i in $(find . -type d -depth 1 | grep -v .git | cut -d\/ -f 2) ;
          do make clean SERVICE=$i ; done'
        - 'for i in $(find . -type d -depth 1 | grep -v .git | cut -d\/ -f 2) ;
          do make build SERVICE=$i ; done'
    - Then run with a test event:
        'sam local invoke 'awsBidsAlexaSkill' --skip-pull-image -e
        alexa/emailDirectors.json --env-vars env.json --docker-network
        localstack'
