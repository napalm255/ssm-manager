const { createApp, ref, computed, onMounted } = Vue;

const app = createApp({
    setup() {
        const title = ref("SSM Manager");
        const version = ref("");
        const githubUrl = ref('https://github.com/napalm255/ssm-manager');

        const currentPage = ref("Start");
        const currentHash = ref('#/start');
        const health = ref("");

        const profiles = ref([]);
        const regionsAll = ref([]);
        const regionsSelected = ref([]);
        const preferences = ref({});

        const prefPortStart = ref(60000);
        const prefPortEnd = ref(65535);
        const prefLogLevel = ref('INFO');
        const prefRegions = ref([]);

        const tooltipTriggerList = ref([]);
        const tooltipList = ref([]);

        const navBar = ref([
          {'name': 'Home', 'icon': 'fa-solid fa-house fa-lg', 'hash': '#/home'},
          {'name': 'Instances', 'icon': 'fa-solid fa-server fa-lg', 'hash': '#/instances'},
          {'name': 'Preferences', 'icon': 'fa-solid fa-gear fa-lg', 'hash': '#/preferences'},
          {'name': 'Profiles', 'icon': 'fa-solid fa-users fa-lg', 'hash': '#/profiles'}
        ]);

        const updateHash = async () => {
          currentHash.value = window.location.hash;
          switch (currentHash.value) {
            case '#/home':
              switchPage('Home');
              break;
            case '#/instances':
              switchPage('Instances');
              break;
            case '#/preferences':
              switchPage('Preferences');
              break;
            case '#/profiles':
              switchPage('Profiles');
              break;
            default:
              switchPage('Start');
          }
        }

        const switchPage = async (page) => {
          const homePage = document.getElementById('home');
          const instancesPage = document.getElementById('instances');
          const preferencesPage = document.getElementById('preferences');
          const profilesPage = document.getElementById('profiles');
          switch (page) {
            case "Start":
              if (profiles.value.length === 0) {
                switchPage('Home')
              } else {
                switchPage('Instances');
              }
              break;
            case "Home":
              currentPage.value = "Home";
              homePage.style.display = 'block';
              instancesPage.style.display = 'none';
              preferencesPage.style.display = 'none';
              profilesPage.style.display = 'none';
              window.location.hash = '#/home';
              currentHash.value = '#/home';
              localStorage.setItem('lastPage', 'Home');
              break;
            case "Instances":
              currentPage.value = "Instances";
              homePage.style.display = 'none';
              instancesPage.style.display = 'block';
              preferencesPage.style.display = 'none';
              profilesPage.style.display = 'none';
              window.location.hash = '#/instances';
              currentHash.value = '#/instances';
              localStorage.setItem('lastPage', 'Instances');
              break;
            case "Preferences":
              currentPage.value = "Preferences";
              homePage.style.display = 'none';
              instancesPage.style.display = 'none';
              preferencesPage.style.display = 'block';
              profilesPage.style.display = 'none';
              window.location.hash = '#/preferences';
              currentHash.value = '#/preferences';
              localStorage.setItem('lastPage', 'Preferences');
              break;
            case "Profiles":
              currentPage.value = "Profiles";
              homePage.style.display = 'none';
              instancesPage.style.display = 'none';
              preferencesPage.style.display = 'none';
              profilesPage.style.display = 'block';
              window.location.hash = '#/profiles';
              currentHash.value = '#/profiles';
              localStorage.setItem('lastPage', 'Profiles');
              break;
          }
        }

        const getVersion = async () => {
          console.log('Fetching version...');
          await fetch("/api/version", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            version.value = data.version;
            title.value = data.name;
            console.log('Version fetched:', version.value);
          })
          .catch((error) => console.error("Error fetching version:", error));
        };

        const profilesTableColumns = ref([
          { title: 'Profile Name', field: 'name' },
          { title: 'Output Format', field: 'output' },
          { title: 'Region', field: 'region' },
          { title: 'Account ID', field: 'sso_account_id' },
          { title: 'Role Name', field: 'sso_role_name' },
          { title: 'Session Name', field: 'sso_session' }
        ]);

        const getProfiles = async () => {
          console.log('Fetching profiles...');
          await fetch("/api/profiles", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            profiles.value = data;
            console.log('Profiles fetched:', profiles.value);
          })
          .catch((error) => console.error("Error fetching profiles:", error));
        };

        const getRegionsAll = async () => {
          console.log('Fetching all regions...');
          await fetch("/api/regions/all", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            regionsAll.value = data;
            console.log('All regions fetched:', regionsAll.value);
          })
          .catch((error) => console.error("Error fetching all regions:", error));
        };

        const getRegionsSelected = async () => {
          console.log('Fetching selected regions...');
          await fetch("/api/regions", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            regionsSelected.value = data;
            console.log('Selected regions fetched:', regionsSelected.value);
          })
          .catch((error) => console.error("Error fetching selected regions:", error));
        };

        const getPreferences = async () => {
          console.log('Fetching preferences...');
          await fetch("/api/preferences", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            preferences.value = data;
            console.log('Preferences fetched:', preferences.value);

            const portRange = preferences.value.port_range || { start: 60000, end: 65535 };
            const logging = preferences.value.logging || { level: 'INFO' };
            const regions = preferences.value.regions || [];
            prefPortStart.value = portRange.start;
            prefPortEnd.value = portRange.end;
            prefLogLevel.value = logging.level;
            prefRegions.value = regions;
          })
          .catch((error) => console.error("Error fetching preferences:", error));
        };

        const savePreferences = async () => {
          console.log('Saving preferences...');
          console.log('Port Start:', prefPortStart.value);
          console.log('Port End:', prefPortEnd.value);
          console.log('Log Level:', prefLogLevel.value);
          console.log('Selected Regions:', prefRegions.value);

          const newPreferences = {
            port_range: {
              start: prefPortStart.value,
              end: prefPortEnd.value
            },
            logging: {
              level: prefLogLevel.value
            },
            regions: prefRegions.value
          };

          await fetch("/api/preferences", {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(newPreferences)
          })
          .then((response) => response.json())
          .then((data) => {
            if (!data.status || data.status !== 'success') {
              throw new Error('Failed to save preferences');
            };
            console.log('Preferences saved:', data);
            dataRefresh();
          })
          .catch((error) => console.error("Error fetching preferences:", error));
        };

        const dataRefresh = async () => {
          console.log('Refreshing data...');
          await getVersion();
          await getProfiles();
          await getRegionsAll();
          await getRegionsSelected();
          await getPreferences();
        };

		const themeToggle = async () => {
          const body = document.body;
          const currentTheme = body.getAttribute('data-bs-theme');
          const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
          body.setAttribute('data-bs-theme', newTheme);
          localStorage.setItem('lastTheme', newTheme);
        };

        const serverPort = async () => {
          return window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
        };

        const serverHost = async () => {
          return window.location.hostname;
        }

        onMounted(async () => {
          // Set the initial theme
          const lastTheme = localStorage.getItem('lastTheme');
          if (lastTheme) {
            document.body.setAttribute('data-bs-theme', lastTheme);
          }

          // Set the initial page
          const lastPage = localStorage.getItem('lastPage');
          if (lastPage) {
            await switchPage(lastPage);
          } else {
            await switchPage('Start');
          }

          // Refresh the data
          await dataRefresh();

          // Initialize tooltips
          tooltipTriggerList.value = document.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltipList.value = [...tooltipTriggerList.value].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

          // Watch for hash changes
          window.addEventListener('hashchange', updateHash);

        });

        return {
          title, version, githubUrl, navBar, switchPage, currentPage, currentHash, health, themeToggle,
          profiles, profilesTableColumns, regionsSelected, regionsAll,
          preferences, savePreferences, prefPortStart, prefPortEnd, prefLogLevel, prefRegions,
          tooltipTriggerList, tooltipList
        };
    }
});
app.mount("#app");
