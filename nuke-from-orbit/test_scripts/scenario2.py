import os
from realbrowserlocusts import ChromeLocust
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from locust import TaskSet, task, between
import looker_sdk
import random

SITE = "https://sharonpbl.looker.com"

## dashboard path possibilities
dash_id = [
            "/19?Date=90%20days", 
            "/19?Date=180%20days",
            "/19?Date=365%20days",
            "/17?Date=90%20days&State=New%20York",
            "/17?Date=180%20days&State=New%20York",
            "/17?Date=365%20days&qState=New%20York",
            "/17?Date=90%20days&State=California",
            "/17?Date=180%20days&State=California",
            "/17?Date=365%20days&State=California",
            "/17?Date=90%20days&State=Texas",
            "/17?Date=180%20days&State=Texas",
            "/17?Date=365%20days&State=Texas",
            "/18?Date=7%20days&Browser=Chrome", 
            "/18?Date=14%20days&Browser=Chrome",
            "/18?Date=30%20days&Browser=Chrome",
            "/18?Date=7%20days&Browser=IE", 
            "/18?Date=14%20days&Browser=IE",
            "/18?Date=30%20days&Browser=IE",
            "/18?Date=7%20days&Browser=Firefox", 
            "/18?Date=14%20days&Browser=Firefox",
            "/18?Date=30%20days&Browser=Firefox",
            "/18?Date=7%20days&Browser=Safari", 
            "/18?Date=14%20days&Browser=Safari",
            "/18?Date=30%20days&Browser=Safari"
          ]

#DASH_PATH= random.choice(dash_id)

#explore path possibilities
explore_id = [
    "thelook/order_items?toggle=dat,fil,vis&qid=aLRS5ixI0q3G6Rk1yW6L99",
    "thelook/order_items?toggle=fil,vis,vse&qid=qry6EID7TMjxxBlfxFsCmX",
    "thelook/order_items?toggle=fil,vis&qid=yVX99oFCL5MvPOq2JAiuqT",
    "thelook/sessions?qid=EJZ99yHQkFBYBnDER9vyj1"
]

##create unique user_id for each web session
users=random.randint(0,100000)

## brand user attribute possibilities
brand = ["Calvin Klein", "Carhartt", "Allegra K","Dockers","Levi's"]

sdk=looker_sdk.init31()

class LocustUserBehavior(TaskSet):

    #automatically called by locust
    def on_start(self):
        #create sso embed user url via API
        embed_params =looker_sdk.models.EmbedSsoParams(
            target_url=SITE+"/dashboards"+f"{random.choice(dash_id)}", 
            session_length=10000, 
            force_logout_login=True, 
            external_user_id= f"{str(random.randint(0,100000))}", 
            first_name= "Embed", 
            last_name= "User", 
            permissions=["access_data", "see_looks", "see_user_dashboards", "see_drill_overlay","explore"], 
            models=["thelook"], 
            group_ids=[12058, 11],
            user_attributes= {"brand":f"{random.choice(brand)}"}
        )
        
        #create embed user+ get embed user credentials
        self.embed_url=sdk.create_sso_embed_url(embed_params)
        #run sso url -establish valid embed session
        self.client.get(self.embed_url.url)
        # self.login()
        
    #automatically called by locust
    def on_stop(self):
        self.logout()

    def login(self):
        self.client.get(SITE + "/login")

        user_entry = os.getenv("USERNAME")
        pass_entry = os.getenv("PASS")
        username = self.client.find_element_by_id("login-email")
        pw = self.client.find_element_by_id("login-password")
        box = self.client.find_element_by_class_name("checkbox")
        username.clear()
        username.send_keys(user_entry)
        pw.clear()
        pw.send_keys(pass_entry)
        box.click()
        self.client.find_element_by_id("login-submit").click()

    def logout(self):
        print("stopping session")

    def open_dashboard(self):
        script = """
        window.awaitPerformanceObservation("rendered").then(function() {
            var dash_render = document.createElement("div");
            dash_render.id = "dash_listener";
            document.body.appendChild(dash_render);
        });"""

        try:
            self.client.get(f"{SITE}/embed/dashboards{str(random.choice(dash_id))}")

            self.client.execute_script(script)

            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "dash_listener")
                )
            )
        except TimeoutException:
            print("hit timeout")

    def open_sso_dashboard(self):
        script = """
        window.awaitPerformanceObservation("rendered").then(function() {
            var dash_render = document.createElement("div");
            dash_render.id = "dash_listener";
            document.body.appendChild(dash_render);
        });"""

        try:
            self.client.get(self.embed_url.url)
            self.client.execute_script(script)
            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "dash_listener")
                )
            )
            self.client.get(f"{SITE}/embed/dashboards{str(random.choice(dash_id))}")

            self.client.execute_script(script)

            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "dash_listener")
                )
            )



        except TimeoutException:
            print("hit open sso timeout")

    def open_explore(self):
        script = """
        window.awaitPerformanceObservation("rendered").then(function() {
            var dash_render = document.createElement("div");
            dash_render.id = "finished";
            document.body.appendChild(render);
        });"""

        try:
            self.client.get(f"{SITE}/embed/explore/{str(random.choice(explore_id))}")

            self.client.execute_script(script)

            self.client.wait.until(
                EC.presence_of_element_located(
                    (By.ID, "finished")
                )
            )
        except TimeoutException:
            print("hit timeout")

#tasks
#@tasks(1) - create sso url via api; load /login/embed
#@task(80) - load /embed/dashboards/(id)
#@task(20) - load /embed/explore/...
#(leave out for now) @task() - some background API activity

    #open dashboard
    @task(6)
    def embed_dashboard_loading(self):
        self.client.timed_event_for_locust(
            "Load", "embed dashboard",
            self.open_dashboard
        )
    ##open sso dashboard
    @task(1)
    def sso_dashboard_loading(self):
        self.client.timed_event_for_locust(
            "Load", "sso dashboard",
            self.open_sso_dashboard
        )
    ##open explore
    @task(2)
    def embed_explore_loading(self):
        self.client.timed_event_for_locust(
            "Load", "explore",
            self.open_explore
        )

class LocustUser(ChromeLocust):

    host = "dashboard load test"
    timeout = 15  # in seconds in waitUntil thingies
    wait_time = between(5, 10)
    screen_width = 1200
    screen_height = 600
    task_set = LocustUserBehavior
