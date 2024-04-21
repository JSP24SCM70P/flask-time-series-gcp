'''
Goal of Flask Microservice:
1. Flask will take the repository_name such as angular, angular-cli, material-design, D3 from the body of the api sent from React app and 
   will utilize the GitHub API to fetch the created and closed issues. Additionally, it will also fetch the author_name and other 
   information for the created and closed issues.
2. It will use group_by to group the data (created and closed issues) by month and will return the grouped data to client (i.e. React app).
3. It will then use the data obtained from the GitHub API (i.e Repository information from GitHub) and pass it as a input request in the 
   POST body to LSTM microservice to predict and forecast the data.
4. The response obtained from LSTM microservice is also return back to client (i.e. React app).

Use Python/GitHub API to retrieve Issues/Repos information of the past 1 year for the following repositories:
- https: // github.com/angular/angular
- https: // github.com/angular/material
- https: // github.com/angular/angular-cli
- https: // github.com/d3/d3
'''
# Import all the required packages 
import os
from flask import Flask, jsonify, request, make_response, Response, render_template
from flask_cors import CORS
import json
import dateutil.relativedelta
from dateutil import *
from datetime import date
import pandas as pd
import requests
import time
import re

# Initilize flask app
app = Flask(__name__)
# Handles CORS (cross-origin resource sharing)
CORS(app)

# Add response headers to accept all types of  requests
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

# Modify response headers when returning to the origin
def build_actual_response(response):
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

'''
function to handle pagination of github api. This will ensure we get all data from linked pages
'''
def pagination(search_issues_headers, query_url, token, type):
    headers = {
        "Authorization": f'token {token}'
    }
    params = {
        "state": "open"
    }
    issues_items = []
    if 'Link' in search_issues_headers:
            links = search_issues_headers.get("Link")
            if 'rel="last"' in links:
                pattern = r'<([^>]+)>; rel="last"'

                # Extract the URL for the last page
                last_page_url = re.search(pattern, links).group(1)

                # Parse the URL to get last page number
                last_page_number = int(last_page_url.split('page=')[-1])
                
                # Fetch issues for remaining pages
                for page_number in range(2, last_page_number + 1):
                    params["page"] = page_number
                    inter_result = requests.get(query_url, headers=headers, params=params)
                    inter_result = inter_result.json()
                    '''
                    code to handle github API rate limit 
                    '''
                    while(True):
                        if('message' in inter_result):
                            time.sleep(10)
                            inter_result = requests.get(query_url, headers=headers, params=params)
                            
                            inter_result= inter_result.json()
                            #inter_result = inter_result.get("items")
                        else:
                            break
                    #inter_result = inter_result.json()
                    if type == "issue":
                        inter_result = inter_result.get("items")
                        issues_items.extend(inter_result)
                    elif type == "commit":
                        issues_items.extend(inter_result)
                    elif type == "releases":
                        issues_items.extend(inter_result)
    return issues_items


@app.route('/') 
def home():
    return render_template('home.html')
'''
API route path is  "/api/forecast"
This API will accept only POST request
'''
@app.route('/api/github', methods=['POST'])
def github():
    body = request.get_json()
    # Extract the choosen repositories from the request
    repo_name = body['repository']
    starlist_status = body['starlist_status']
    forklist_status = body['forklist_status']
    linechart_status = body['linechart_status']
    stackissues_status = body['stackissues_status']
    # Add your own GitHub Token to run it local
    token = os.environ.get(
        'GITHUB_TOKEN')
    GITHUB_URL = f"https://api.github.com/"
    headers = {
        "Authorization": f'token {token}'
    }
    params = {
        "state": "open"
    }


    #if block will return the star count of each repo if starlist_status is request body is true

    if(starlist_status):
        stars_count = []
        repo_name = repo_name.split()
        for r in repo_name:
            repository_url = GITHUB_URL + "repos/" + r
            # Fetch GitHub data from GitHub API
            repository = requests.get(repository_url, headers=headers)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            stars = repository["stargazers_count"]
            temp_arr = [r, stars]
            stars_count.append(temp_arr)
        json_response = {
            "starsCount": stars_count
        }
        return jsonify(json_response)
    

    #if block will return the fork count of each repo if forklist_status is request body is true

    if(forklist_status):
        forks_count = []
        repo_name = repo_name.split('$')
        for r in repo_name:
            repository_url = GITHUB_URL + "repos/" + r
            # Fetch GitHub data from GitHub API
            repository = requests.get(repository_url, headers=headers)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            forks = repository["forks_count"]
            temp_arr = [r, forks]
            forks_count.append(temp_arr)
        json_response = {
            "forksCount": forks_count
        }
        return jsonify(json_response)
    
    if(linechart_status):
        issues_count = []
        today = date.today()
        last_month = today + dateutil.relativedelta.relativedelta(months=-24)
        repo_name = repo_name.split('*')
        for r in repo_name:
            params = {
            "state": "open"
            }
            repo = 'repo:' + r
            ranges = 'created:' + str(last_month) + '..' + str(today)
            types = 'type:issue'
            per_page = 'per_page=100'
            
            search_query = repo + ' ' + ranges + ' ' + types

            # Append the search query to the GitHub API URL 
            query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
            # Fetch GitHub data from GitHub API
            repository = requests.get(query_url, headers=headers, params=params)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            issues = repository["total_count"]
            temp_arr = [r, issues]
            issues_count.append(temp_arr)
        json_response = {
            "issuesCount": issues_count
        }
        return jsonify(json_response)
    
    if(stackissues_status):
        issues_count = []
        issues_count_close = []
        today = date.today()
        last_month = today + dateutil.relativedelta.relativedelta(months=-24)
        repo_name = repo_name.split('@')
        for r in repo_name:
            params = {
            "state": "open"
            }
            repo = 'repo:' + r
            ranges = 'created:' + str(last_month) + '..' + str(today)
            types = 'type:issue'
            per_page = 'per_page=100'
            state_open = 'state:open'
            state_close = 'state:closed'
            search_query = repo + ' ' + ranges + ' ' + types

            # Append the search query to the GitHub API URL 
            query_url = GITHUB_URL + "search/issues?q=" + search_query + ' ' + state_open + "&" + per_page
            query_url_close = GITHUB_URL + "search/issues?q=" + search_query + ' ' + state_close + "&" + per_page
            # Fetch GitHub data from GitHub API
            repository = requests.get(query_url, headers=headers, params=params)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            issues = repository["total_count"]
            temp_arr = [r, issues]
            issues_count.append(temp_arr)

            repository = requests.get(query_url_close, headers=headers, params=params)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            issues_close = repository["total_count"]
            temp_arr = [r, issues_close]
            issues_count_close.append(temp_arr)
        json_response = {
            "issuesCountOpen": issues_count,
            "issuesCountClosed": issues_count_close
        }
        return jsonify(json_response)
    
    repository_url = GITHUB_URL + "repos/" + repo_name
    # Fetch GitHub data from GitHub API
    repository = requests.get(repository_url, headers=headers)
    # Convert the data obtained from GitHub API to JSON format
    repository = repository.json()

    today = date.today()
    date_24m_back = today
    issues_reponse = []   # for type: issues
    pull_responses = []   # for type:pr
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        params = {
        "state": "open"
        }
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        #types = 'type:issue'   #commenting because if this is not included, it returns both issues and pulls
        repo = 'repo:' + repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = repo + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)
        search_issues_headers = search_issues.headers
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        
        issues_items = []

        '''
        code to handle github API rate limit 
        '''
        while(True):
            if('message' in search_issues):
                time.sleep(10)
                search_issues = requests.get(query_url, headers=headers, params=params)
                # Convert the data obtained from GitHub API to JSON format
                search_issues = search_issues.json()
            else:
                break
        
        
        try:
            # Extract "items" from search issues
            issues_items = search_issues.get("items")
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        
        total_count = search_issues.get("total_count")
        if total_count > 0 and len(issues_items) == 0:
            #time.sleep(10) # just in case if there is a mismatch
            search_issues = requests.get(query_url, headers=headers, params=params)
            search_issues = search_issues.json()    
        
        '''
        fetching remaining issues from linked pages
        '''
        pagination_response = pagination(search_issues_headers,query_url, token, "issue")
        issues_items.extend(pagination_response)
        
        if issues_items is None:
            continue
        for issue in issues_items:
            label_name = []
            data = {}
            current_issue = issue
            # Get issue number
            data['issue_number'] = current_issue["number"]
            # Get created date of issue
            if 'pull_request' in current_issue:
                data['pull_created_at'] = current_issue["created_at"][0:10]                # key name 'pull_request' will be present for pull requests
            else:
                data['created_at'] = current_issue["created_at"][0:10]
            #data['created_at'] = current_issue["created_at"][0:10]
            if current_issue["closed_at"] == None:
                data['closed_at'] = current_issue["closed_at"]
            else:
                # Get closed date of issue
                data['closed_at'] = current_issue["closed_at"][0:10]
            for label in current_issue["labels"]:
                # Get label name of issue
                label_name.append(label["name"])
            data['labels'] = label_name
            # It gives state of issue like closed or open
            data['State'] = current_issue["state"]
            # Get Author of issue
            data['Author'] = current_issue["user"]["login"]
            if 'pull_request' in current_issue:
                pull_responses.append(data)                # key name 'pull_request' will be present for pull requests
            else:
                issues_reponse.append(data)

        today = last_month
        date_24m_back = last_month
    

    '''
    fetch commits data from the requested repository
    '''
   
    ranges = 'since=' + str(date_24m_back)
    per_page = 'per_page=100'


    # Append the search query to the GitHub API URL 
    query_url_commits = repository_url + "/commits?" + ranges + "&" + per_page
    # requsets.get will fetch requested query_url from the GitHub API
    commits_response = requests.get(query_url_commits, headers=headers, params=params)
    commits_response_headers = commits_response.headers
    # Convert the data obtained from GitHub API to JSON format
    commits_response = commits_response.json()

    pagination_response_commits = pagination(commits_response_headers,query_url_commits, token, "commit")
    commits_response.extend(pagination_response_commits)

    commits_list = []

    for commit in commits_response:
        label_name = []
        data = {}
        current_commit = commit
        if current_commit['commit']['committer'] is not None:
            data['commit_created_at'] = current_commit['commit']['committer']['date'][0:10]
            data['issue_number'] = current_commit['sha']
            commits_list.append(data)

    '''
    fetch releases data from the requested repository
    '''
    
    #per_page = 'per_page=100'
    
    # Append the search query to the GitHub API URL 
    query_url_releases = repository_url + "/releases?" + per_page
    # requsets.get will fetch requested query_url from the GitHub API
    releases_response = requests.get(query_url_releases, headers=headers, params=params)
    releases_response_headers = releases_response.headers
    # Convert the data obtained from GitHub API to JSON format
    releases_response = releases_response.json()

    pagination_response_releases = pagination(releases_response_headers,query_url_releases, token, "releases")
    releases_response.extend(pagination_response_releases)

    releases_list = []

    for release in releases_response:
        label_name = []
        data = {}
        current_release = release
        if current_release is not None:
            data['release_created_at'] = current_release['created_at'][0:10]
            data['published_at'] = current_release['published_at'][0:10]
            data['issue_number'] = current_release['id']
            data['url'] = current_release['url']
            releases_list.append(data)

    df = pd.DataFrame(issues_reponse)
    df_pull = pd.DataFrame(pull_responses)   # pull requests dataframe

    # Daily Created Issues
    df_created_at = df.groupby(['created_at'], as_index=False).count()
    dataFrameCreated = df_created_at[['created_at', 'issue_number']]
    dataFrameCreated.columns = ['date', 'count']

    '''
    Monthly Created Issues
    Format the data by grouping the data by month
    ''' 
    created_at = df['created_at']
    month_issue_created = pd.to_datetime(
        pd.Series(created_at), format='%Y-%m-%d')
    month_issue_created.index = month_issue_created.dt.to_period('m')
    month_issue_created = month_issue_created.groupby(level=0).size()
    month_issue_created = month_issue_created.reindex(pd.period_range(
        month_issue_created.index.min(), month_issue_created.index.max(), freq='m'), fill_value=0)
    month_issue_created_dict = month_issue_created.to_dict()
    created_at_issues = []
    for key in month_issue_created_dict.keys():
        array = [str(key), month_issue_created_dict[key]]
        created_at_issues.append(array)

    '''
    Monthly Closed Issues
    Format the data by grouping the data by month
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    month_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y-%m-%d')
    month_issue_closed.index = month_issue_closed.dt.to_period('m')
    month_issue_closed = month_issue_closed.groupby(level=0).size()
    date_a = date.today().strftime('%Y-%m-%d')
    date_b = date_24m_back.strftime('%Y-%m-%d')
    if all(value is None for value in month_issue_closed):
        month_issue_closed = pd.Series(0,index=pd.period_range(start=date_b, end=date_a, freq='m'))
    else:
        month_issue_closed = month_issue_closed.reindex(pd.period_range(
            month_issue_closed.index.min(), month_issue_closed.index.max(), freq='m'), fill_value=0)
    month_issue_closed_dict = month_issue_closed.to_dict()
    closed_at_issues = []
    for key in month_issue_closed_dict.keys():
        array = [str(key), month_issue_closed_dict[key]]
        closed_at_issues.append(array)
    
    '''
    weekly Closed Issues
    Format the data by grouping the data by week
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    week_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y-%m-%d')
    week_issue_closed.index = week_issue_closed.dt.to_period('w')
    week_issue_closed = week_issue_closed.groupby(level=0).size()
    date_a = date.today().strftime('%Y-%m-%d')
    date_b = date_24m_back.strftime('%Y-%m-%d')
    if all(value is None for value in week_issue_closed):
        week_issue_closed = pd.Series(0,index=pd.period_range(start=date_b, end=date_a, freq='w'))
    else:
        week_issue_closed = week_issue_closed.reindex(pd.period_range(
            week_issue_closed.index.min(), week_issue_closed.index.max(), freq='w'), fill_value=0)
    week_issue_closed_dict = week_issue_closed.to_dict()
    closed_at_issues_week = []
    for key in week_issue_closed_dict.keys():
        array = [str(key), week_issue_closed_dict[key]]
        closed_at_issues_week.append(array)

    '''
        1. Hit LSTM Microservice by passing issues_response as body
        2. LSTM Microservice will give a list of string containing image paths hosted on google cloud storage
        3. On recieving a valid response from LSTM Microservice, append the above json_response with the response from
            LSTM microservice
    '''
    created_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }
    closed_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    }
    pull_requests_created_body = {
        "issues": pull_responses,
        "type": "pull_created_at",
        "repo": repo_name.split("/")[1],
        "issue_type": "pulls"
    }
    commits_created_body = {
        "issues": commits_list,
        "type": "commit_created_at",
        "repo": repo_name.split("/")[1],
        "issue_type": "commits"
    }
    releases_created_body = {
        "issues": releases_list,
        "type": "release_created_at",
        "repo": repo_name.split("/")[1],
        "issue_type": "releases"
    }

    # Update your Google cloud deployed LSTM app URL (NOTE: DO NOT REMOVE "/")
    LSTM_API_URL = "https://lstm-forecast-mx3slx5rea-uc.a.run.app/" + "api/forecast"
    LSTM_API_URL_STAT = "https://lstm-forecast-mx3slx5rea-uc.a.run.app/" + "api/stat"
    LSTM_API_URL_FB = "https://lstm-forecast-mx3slx5rea-uc.a.run.app/" + "api/fbprophet"
    """ LSTM_API_URL = "http://127.0.0.1:8080/" + "api/forecast"
    LSTM_API_URL_STAT = "http://127.0.0.1:8080/" + "api/stat"
    LSTM_API_URL_FB = "http://127.0.0.1:8080/" + "api/fbprophet" """
    '''
    Trigger the LSTM microservice to forecasted the created issues  (stat model)
    The request body consists of created issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    closed_at_response_fb = requests.post(LSTM_API_URL_FB,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    created_at_response = requests.post(LSTM_API_URL,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})
    created_at_response_stat = requests.post(LSTM_API_URL_STAT,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})
    created_at_response_fb = requests.post(LSTM_API_URL_FB,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})
    

    '''
    Trigger the LSTM microservice to forecasted the created issues
    The request body consists of created issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    
    
    '''
    Trigger the LSTM microservice to forecasted the closed issues
    The request body consists of closed issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''    
    closed_at_response = requests.post(LSTM_API_URL,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    closed_at_response_stat = requests.post(LSTM_API_URL_STAT,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    
    
    
    '''
    Trigger the LSTM microservice to forecasted the pull issues
    The request body consists of pull issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    pull_created_at_response = requests.post(LSTM_API_URL,
                                       json=pull_requests_created_body,
                                       headers={'content-type': 'application/json'})
    pull_created_at_response_stat = requests.post(LSTM_API_URL_STAT,
                                       json=pull_requests_created_body,
                                       headers={'content-type': 'application/json'})
    
    '''
    Trigger the LSTM microservice to forecasted the commits
    The request body consists of commits obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    commits_created_at_response = requests.post(LSTM_API_URL,
                                       json=commits_created_body,
                                       headers={'content-type': 'application/json'})
    commits_created_at_response_stat = requests.post(LSTM_API_URL_STAT,
                                       json=commits_created_body,
                                       headers={'content-type': 'application/json'})
    
    '''
    Trigger the LSTM microservice to forecasted the releases
    The request body consists of releases obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    releases_created_at_response = requests.post(LSTM_API_URL,
                                       json=releases_created_body,
                                       headers={'content-type': 'application/json'})
    releases_created_at_response_stat = requests.post(LSTM_API_URL_STAT,
                                       json=releases_created_body,
                                       headers={'content-type': 'application/json'})
    
    
    
    
    '''
    Create the final response that consists of:
        1. GitHub repository data obtained from GitHub API
        2. Google cloud image urls of created and closed issues obtained from LSTM microservice
    '''
    json_response = {
        "created": created_at_issues,
        "closed": closed_at_issues,
        "week_closed": closed_at_issues_week,
        "starCount": repository["stargazers_count"],
        "forkCount": repository["forks_count"],
        "createdAtImageUrls": {
            **created_at_response.json(),
        },
        "closedAtImageUrls": {
            **closed_at_response.json(),
        },
        "pulledAtImageUrls": {
            **pull_created_at_response.json(),
        },
        "commitsAtImageUrls": {
            **commits_created_at_response.json(),
        },
        "releasesAtImageUrls": {
            **releases_created_at_response.json(),
        },
        "createdAtStatImageUrls": {
            **created_at_response_stat.json(),
        },
        "closedAtStatImageUrls": {
            **closed_at_response_stat.json(),
        },
        "pulledAtStatImageUrls": {
            **pull_created_at_response_stat.json(),
        },
        "commitsAtStatImageUrls": {
            **commits_created_at_response_stat.json(),
        },
        "releasesAtStatImageUrls": {
            **releases_created_at_response_stat.json(),
        },
        "createdAtFbImageUrls": {
            **created_at_response_fb.json(),
        },
        "closedAtFbImageUrls": {
            **closed_at_response_fb.json(),
        },
    }
    # Return the response back to client (React app)
    return jsonify(json_response)


# Run flask app server on port 5000
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
