const { createApp, ref, computed, onMounted, onUnmounted, watch } = Vue;

const app = createApp({
    setup() {
        const title = ref("SSM Manager");
        const version = ref("");
        const githubUrl = ref('https://github.com/napalm255/ssm-manager');

        const currentPage = ref("Start");
        const currentHash = ref('#/start');
        const currentProfile = ref("Select Profile");
        const currentRegion = ref("Select Region");
        const currentAccountId = ref("");
        const health = ref("");

        const profiles = ref([]);
        const profilesCount = computed(() => {
          return profiles.value.length;
        });

        const regionsAll = ref([]);
        const regionsSelected = ref([]);

        const preferences = ref({});
        const prefPortStart = ref(60000);
        const prefPortEnd = ref(65535);
        const prefLogLevel = ref('INFO');
        const prefRegions = ref([]);
        const prefPortCount = computed(() => {
          return prefPortEnd.value - prefPortStart.value + 1;
        });
        const prefRegionsCount = computed(() => {
          return prefRegions.value.length;
        });

        const tooltipTriggerList = ref([]);
        const tooltipList = ref([]);

        const isConnecting = ref(false);

        const instances = ref([]);
        const instancesCount = ref(0);

        const activeConnections = ref([]);
        const activeConnectionsCount = ref(0);
        const intervalActiveConnections = ref(null);

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
          console.debug('Fetching version...');
          await fetch("/api/version", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            version.value = data.version;
            title.value = data.name;
            console.log('Version:', version.value);
          })
          .catch((error) => console.error('Error fetching version:', error));
        };

        const profilesTableColumns = ref([
          { title: 'Profile Name', field: 'name' },
          { title: 'Account ID', field: 'sso_account_id' },
          { title: 'Region', field: 'region' },
          { title: 'Role Name', field: 'sso_role_name' },
          { title: 'Session Name', field: 'sso_session' }
        ]);

        const getProfiles = async () => {
          console.debug('Fetching profiles...');
          await fetch("/api/profiles", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            profiles.value = data;
          })
          .catch((error) => console.error('Error fetching profiles:', error));
        };

        const getRegionsAll = async () => {
          console.debug('Fetching all regions...');
          await fetch("/api/regions/all", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            regionsAll.value = data;
          })
          .catch((error) => console.error('Error fetching all regions:', error));
        };

        const getRegionsSelected = async () => {
          console.debug('Fetching selected regions...');
          await fetch("/api/regions", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            regionsSelected.value = data;
          })
          .catch((error) => console.error('Error fetching selected regions:', error));
        };

        const getPreferences = async () => {
          console.debug('Fetching preferences...');
          await fetch("/api/preferences", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            preferences.value = data;
            console.debug('Loaded Preferences:', preferences.value);

            const portRange = preferences.value.port_range || { start: 60000, end: 65535 };
            const logging = preferences.value.logging || { level: 'INFO' };
            const regions = preferences.value.regions || [];
            prefPortStart.value = portRange.start;
            prefPortEnd.value = portRange.end;
            prefLogLevel.value = logging.level;
            prefRegions.value = regions;
          })
          .catch((error) => console.error('Error fetching preferences:', error));
        };

        const savePreferences = async () => {
          console.debug('Saving preferences...');

          if (!validatePortRange(prefPortStart.value, prefPortEnd.value)) {
            console.error('Invalid port range:', prefPortStart.value, prefPortEnd.value);
            return;
          }

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
              throw new Error(data.status || 'Unknown error');
            };
            console.log('Preferences saved successfully:', data);
            toast('Preferences saved successfully', 'success');
            dataRefresh();
          })
          .catch((error) => {
            console.error('Error saving preferences:', error)
            toast('Error saving preferences', 'danger');
          });
        };

        const validatePortRange = (start, end) => {
          const validPortStart = start >= 1024 && start <= 65535;
          const validPortEnd = end >= 1024 && end <= 65535;
          const validPortRange = start < end;
          if (!validPortStart) {
            toast('Starting port must be between 1024 and 65535', 'danger');
          }
          if (!validPortEnd) {
            toast('Ending port must be between 1024 and 65535', 'danger');
          }
          if (!validPortRange) {
            toast('Starting port must be less than the ending port', 'danger');
          }
          if (validPortStart && validPortEnd && validPortRange) {
            return true;
          }
          return false;
        };

      // -----------------------------------------------

        const connect = async () => {
          console.debug('Connecting to AWS...');
          isConnecting.value = true;
          await fetch("/api/connect", {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value
            })
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('Connection response:', data);
            if (!data.status || data.status !== 'success') {
              throw new Error(data.error || 'Unknown error');
            }
            currentAccountId.value = data.account_id;
            toast('Connected to AWS successfully', 'success');
            getInstances();
            isConnecting.value = false;
          })
          .catch((error) => {
            console.error('Failed connecting to AWS:', error);
            toast('Failed connecting to AWS', 'danger');
          });
        };

        const getInstances = async () => {
          console.debug('Fetching instances...');
          await fetch("/api/instances", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            console.log('Instances:', data);
            instances.value = data;
            instancesCount.value = instances.value.length;
            toast(`Loaded ${instancesCount.value} instances`, 'success');
          })
          .catch((error) => {
            console.error('Error fetching instances:', error);
            toast('Error fetching instances', 'danger');
          });
        };

        const getActiveConnections = async () => {
          // console.debug('Fetching active connections...');
          await fetch("/api/active-connections", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            // console.debug('Active Connections:', data);
            activeConnectionsCount.value = data.length;
            activeConnections.value = data;
          })
          .catch((error) => console.error('Error fetching active connections:', error));
        };

      // -----------------------------------------------

        watch(currentProfile, (newProfile) => {
          localStorage.setItem('lastProfile', newProfile);
        });

        watch(currentRegion, (newRegion) => {
          localStorage.setItem('lastRegion', newRegion);
        });

      // -----------------------------------------------

        const dataRefresh = async () => {
          console.debug('Refreshing data...');
          await getVersion();
          await getProfiles();
          await getRegionsAll();
          await getRegionsSelected();
          await getPreferences();
        };

        const toast = (message, type = 'info') => {
          const toastContainer = document.getElementById('toast-container');
          const toastElement = document.createElement('div');
          toastElement.className = `toast align-items-center text-bg-${type} border-0`;
          toastElement.setAttribute('role', 'alert');
          toastElement.setAttribute('aria-live', 'assertive');
          toastElement.setAttribute('aria-atomic', 'true');
          toastElement.innerHTML = `
            <div class="d-flex">
              <div class="toast-body">
                ${message}
              </div>
              <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
          `;
          toastContainer.appendChild(toastElement);
          const toastInstance = new bootstrap.Toast(toastElement, {
            delay: 3000,
            autohide: true
          });
          toastInstance.show();
        };

	const themeToggle = async () => {
          const body = document.body;
          const currentTheme = body.getAttribute('data-bs-theme');
          const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
          body.setAttribute('data-bs-theme', newTheme);
          localStorage.setItem('lastTheme', newTheme);
        };

	const hideTooltip = async (event) => {
	  const element = event.currentTarget;
	  const tooltip = bootstrap.Tooltip.getInstance(element);
          if (tooltip) {
            tooltip.hide();
          }
	}

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

          // Set profile and region
          const lastProfile = localStorage.getItem('lastProfile');
          if (lastProfile) {
            currentProfile.value = lastProfile;
          }
          const lastRegion = localStorage.getItem('lastRegion');
          if (lastRegion) {
            currentRegion.value = lastRegion;
          }

          // Initialize tooltips
          tooltipTriggerList.value = document.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltipList.value = [...tooltipTriggerList.value].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

          // Watch for hash changes
          window.addEventListener('hashchange', updateHash);

          // Load data from the server
          await dataRefresh();

          // Query active connections every 2 seconds
          setInterval(getActiveConnections, 2500);

        });

        onUnmounted(async () => {
          // Clean up event listeners
          window.removeEventListener('hashchange', updateHash);

          // Dispose of tooltips
          tooltipList.value.forEach(tooltip => tooltip.dispose());

          // Clear the interval for active connections
          clearInterval(intervalActiveConnections);
        });

        return {
          title, version, githubUrl, navBar, switchPage, currentPage, currentHash, health, themeToggle, hideTooltip,
          profiles, profilesCount, profilesTableColumns, regionsSelected, regionsAll,
          currentProfile, currentRegion, currentAccountId,
          preferences, savePreferences, prefPortStart, prefPortEnd, prefLogLevel, prefRegions, prefPortCount, prefRegionsCount,
          connect, isConnecting,
          getInstances, instances, instancesCount,
          activeConnections, activeConnectionsCount,
          tooltipTriggerList, tooltipList, toast
        };
    }
});
app.mount("#app");
