const { createApp, ref, computed, onMounted, onUnmounted, watch } = Vue;

const app = createApp({
    setup() {
        const title = ref("SSM Manager");
        const version = ref("");
        const operating_system = ref("");
        const githubUrl = ref('https://github.com/napalm255/ssm-manager');

        const currentPage = ref("Start");
        const currentHash = ref('#/start');
        const currentProfile = ref("Select Profile");
        const currentRegion = ref("Select Region");
        const currentAccountId = ref("");

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
        const prefCredentials = ref([]);
        const prefCredentialsToDelete = ref([]);
        const prefCredentialsCount = computed(() => {
          return prefCredentials.value.length;
        });

        const tooltipTriggerList = ref([]);
        const tooltipList = ref([]);

        const isConnecting = ref(false);

        const instances = ref([]);
        const instancesCount = ref(0);
        const instancesDetails = ref({});

        const activeConnections = ref([]);
        const activeConnectionsCount = ref(0);
        const intervalActiveConnections = ref(null);

        const portForwardingModal = ref(null);
        const portForwardingModalProperties = ref({});
        const portForwardingStarting = ref(false);

        const portMappings = computed(() => {
          const mappings = {};
          if (!preferences.value.instances) {
            return mappings;
          }
          for (const instance of preferences.value.instances) {
            mappings[instance.name] = instance.ports;
          }
          return mappings;
        });
        const portMappingsModal = ref(null);
        const portMappingsModalInstance = ref(null);
        const portMappingsModalProperties = ref([]);

        const navBar = ref([
          {'name': 'Home', 'icon': 'bi bi-house-door-fill', 'hash': '#/home'},
          {'name': 'Instances', 'icon': 'bi bi-hdd-rack-fill', 'hash': '#/instances'},
          {'name': 'Preferences', 'icon': 'bi bi-gear-fill', 'hash': '#/preferences'},
          {'name': 'Profiles', 'icon': 'bi bi-person-lines-fill', 'hash': '#/profiles'}
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
            operating_system.value = data.operating_system;
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
            const credentials = preferences.value.credentials || [];
            prefPortStart.value = portRange.start;
            prefPortEnd.value = portRange.end;
            prefLogLevel.value = logging.level;
            prefRegions.value = regions;
            prefCredentials.value = credentials;
            prefCredentialsToDelete.value = [];
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
            regions: prefRegions.value,
            credentials: prefCredentials.value,
            credentials_to_delete: prefCredentialsToDelete.value,
          };
          console.debug('New Preferences:', newPreferences);

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
            console.debug('Preferences saved successfully:', data);
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

        const addCredential = () => {
          console.debug('Adding new credential...');
          prefCredentials.value.push({
            'username': '',
            'password': ''
          });
        };

        const removeCredential = (index) => {
          console.debug('Removing credential at index:', index);
          prefCredentialsToDelete.value.push(prefCredentials.value[index]);
          prefCredentials.value.splice(index, 1);
        }


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
          })
          .catch((error) => {
            console.error('Failed connecting to AWS:', error);
            toast('Failed connecting to AWS', 'danger');
          });
          isConnecting.value = false;
        };

        const disconnect = async (connection_id) => {
          console.debug('Terminating connection:', connection_id);
          await fetch(`/api/terminate-connection/${connection_id}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('Connection response:', data);
            if (!data.status || data.status !== 'success') {
              throw new Error(data.error || 'Unknown error');
            }
            getActiveConnections();
            toast('Connection terminated successfully', 'warning');
          })
          .catch((error) => {
            console.error('Failed to terminate connection:', error);
            toast('Failed to terminate connection', 'danger');
          });
        };

        const getActiveConnections = async () => {
          // console.debug('Fetching active connections...');
          await fetch("/api/active-connections", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('Active Connections:', data);
            activeConnectionsCount.value = data.length;
            activeConnections.value = data;
          })
          .catch((error) => console.error('Error fetching active connections:', error));
        };

        const showPortMappingsModal = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Showing port mappings modal for:', instanceName);
          portMappingsModal.value = new bootstrap.Modal(document.getElementById('portMappingsModal'), {
            keyboard: true
          });
          document.getElementById('portMappingsModal').addEventListener('hidden.bs.modal', () => {
            getPreferences();
          });
          portMappingsModalInstance.value = { id: instanceId, name: name };
          portMappingsModalProperties.value = portMappings.value[instanceName] || [];
          portMappingsModal.value.show();
        };

        const savePortMappings = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Saving port mappings for:', instanceName);

          const validPorts = portMappingsModalProperties.value.filter((mapping) =>
            mapping.local_port && mapping.remote_port
          );

          const newMappings = {
            name: instanceName,
            ports: validPorts
          };

          await fetch(`/api/preferences/${instanceName}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(newMappings)
          })
          .then((response) => response.json())
          .then((data) => {
            if (!data.status || data.status !== 'success') {
              throw new Error(data.status || 'Unknown error');
            };
            console.debug('Port mappings saved successfully:', data);
            toast('Port mappings saved successfully', 'success');
            dataRefresh();
          })
          .catch((error) => {
            console.error('Error saving port mappings:', error)
            toast('Error saving port mappings', 'danger');
          });
          portMappingsModal.value.hide();
        };

        const addPortMapping = () => {
          console.debug('Adding new port mapping...');
          portMappingsModalProperties.value.push({
            local_port: '',
            remote_port: ''
          });
        };

        const removePortMapping = (index) => {
          console.debug('Removing port mapping at index:', index);
          portMappingsModalProperties.value.splice(index, 1);
        };

        const instancesTableColumns = ref([
          { title: 'Name', field: 'name' },
          { title: 'Instance ID', field: 'id' },
          { title: 'OS', field: 'os' },
          { title: 'Type', field: 'type' }
        ]);

        const getInstances = async () => {
          console.debug('Fetching instances...');
          await fetch("/api/instances", {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            instances.value = data;
            instancesDetails[instances.value.id] = {};
            instancesCount.value = instances.value.length;
            toast(`Successfully discovered ${instancesCount.value} instances`, 'success');
          })
          .catch((error) => {
            console.error('Error fetching instances:', error);
            toast('Error fetching instances', 'danger');
          });
        };

        const instanceDetailsColumns = ref([
          { title: 'Name', field: 'name' },
          { title: 'Instance ID', field: 'id' },
          { title: 'AMI ID', field: 'ami_id' },
          { title: 'VPC ID', field: 'vpc_id' },
          { title: 'Subnet ID', field: 'subnet_id' },
          { title: 'IAM Role', field: 'iam_role' },
          { title: 'SSH Key', field: 'ssh_key' },
          { title: 'Private IP', field: 'private_ip' },
          { title: 'Public IP', field: 'public_ip' },
          { title: 'Security Groups', field: 'security_groups' }
        ]);

        const getInstanceDetails = async (instanceId) => {
          console.debug('Fetching instance details...');
          await fetch(`/api/instance-details/${instanceId}`, {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            instancesDetails.value[instanceId] = data;
          })
          .catch((error) => {
            console.error('Error fetching instance details:', error);
            toast('Error fetching instance details', 'danger');
          });
        };

        const startShell = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Starting shell for:', instanceName);
          await fetch(`/api/shell/${instanceId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('Shell started:', data);
            if (!data.status || data.status !== 'active') {
              throw new Error(data.error || 'Unknown error');
            }
            getActiveConnections();
            toast('Successfully started shell', 'success');
          })
          .catch((error) => {
            console.error('Error starting shell:', error);
            toast('Error starting shell', 'danger');
          });
        };

        const startRdp = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Starting RDP for:', instanceName);
          await fetch(`/api/rdp/${instanceId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('RDP started:', data);
            if (!data.status || data.status !== 'active') {
              throw new Error(data.error || 'Unknown error');
            }
            toast('Successfully started RDP', 'success');
            getActiveConnections();
          })
          .catch((error) => {
            console.error('Error starting RDP:', error);
            toast('Error starting RDP', 'danger');
          });
        };

        const openRdpClient = async (instanceId, name, local_port) => {
          const instanceName = name || instanceId;
          console.debug(`Opening RDP to ${instanceName} via port ${local_port}`);
          await fetch(`/api/rdp/${local_port}`, {
            method: 'GET'
          })
          .then((response) => response.json())
          .then((data) => {
            if (!data.status || data.status !== 'success') {
              throw new Error(data.error || 'Unknown error');
            }
            toast('Successfully opened RDP client', 'success');
            getActiveConnections();
          })
          .catch((error) => {
            console.error('Error opening RDP client:', error);
            toast('Error opening RDP client', 'danger');
          });
        };

        const showPortForwardingModal = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Showing port forwarding modal for:', instanceName);
          portForwardingModal.value = new bootstrap.Modal(document.getElementById('portForwardingModal'), {
            keyboard: true
          });
          portForwardingModalProperties.value = {
            instanceId: instanceId,
            instanceName: name,
            mode: 'local',
            remotePort: 1433,
            remoteHost: '',
            credentials: ''
          };
          portForwardingModal.value.show();
        };

        const startPortForwarding = async () => {
          console.debug('Starting port forwarding...');
          portForwardingStarting.value = true;

          await fetch(`/api/custom-port/${portForwardingModalProperties.value.instanceId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: portForwardingModalProperties.value.instanceName,
              mode: portForwardingModalProperties.value.mode,
              remote_port: portForwardingModalProperties.value.remotePort,
              remote_host: portForwardingModalProperties.value.remoteHost,
              credentials: portForwardingModalProperties.value.credentials
            })
          })
          .then((response) => response.json())
          .then((data) => {
            console.debug('Port forwarding started:', data);
            if (!data.status || data.status !== 'active') {
              throw new Error(data.error || 'Unknown error');
            }
            toast('Successfully started port forwarding', 'success');
            getActiveConnections();
          })
          .catch((error) => {
            console.error('Error starting port forwarding:', error);
            toast('Error starting port forwarding', 'danger');
          });
          portForwardingModal.value.hide();
          portForwardingStarting.value = false;
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

        const timeAgo = (timestamp) => {
          const now = Date.now();
          const seconds = Math.floor((now - timestamp * 1000) / 1000);

          const intervals = {
            year: 31536000,
            month: 2592000,
            day: 86400,
            hour: 3600,
            minute: 60,
            second: 1,
          };

          for (const unit in intervals) {
            const interval = intervals[unit];
            const count = Math.floor(seconds / interval);

            if (count >= 1) {
              const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
              return rtf.format(-count, unit);
            }
          }
          return 'just now';
        };

        const copyToClipboard = async (text) => {
          console.debug('Copying to clipboard:', text);
          await navigator.clipboard.writeText(text)
          toast('Copied to clipboard', 'success');
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
            delay: 5000,
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
          title, version, operating_system, githubUrl, navBar, switchPage, currentPage, currentHash, themeToggle, hideTooltip,
          profiles, profilesCount, profilesTableColumns, regionsSelected, regionsAll,
          currentProfile, currentRegion, currentAccountId,
          preferences, getPreferences, savePreferences, prefPortStart, prefPortEnd, prefPortCount, prefLogLevel, prefRegions, prefRegionsCount, portMappings, prefCredentials, prefCredentialsCount,
          addCredential, removeCredential,
          showPortForwardingModal, portForwardingModalProperties, portForwardingStarting,
          showPortMappingsModal, portMappingsModalInstance, portMappingsModalProperties, savePortMappings, addPortMapping, removePortMapping,
          connect, disconnect, isConnecting, startShell, startRdp, openRdpClient, startPortForwarding,
          getInstances, getInstanceDetails, instances, instancesCount, instancesTableColumns, instancesDetails, instanceDetailsColumns,
          activeConnections, activeConnectionsCount, timeAgo,
          tooltipTriggerList, tooltipList, toast, copyToClipboard
        };
    }
});
app.mount("#app");
