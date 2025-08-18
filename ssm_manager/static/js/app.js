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

        const sessions = ref([]);
        const sessionsCount = computed(() => {
          return sessions.value.length;
        });
        const addSessionModal = ref(null);
        const addSessionModalProperties = ref({});

        const profiles = ref([]);
        const profilesCount = computed(() => {
          return profiles.value.length;
        });
        const addProfileModal = ref(null);
        const addProfileModalProperties = ref({});

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
        const portMappingsModalDuplicatePort = computed(() => {
          const allPorts = preferences.value.instances?.flatMap(instance => {
            if (instance.name !== portMappingsModalInstance.value?.name) {
              return instance.ports.map(port => port.local_port);
            }
            return [];
          });
          const modalPorts = portMappingsModalProperties.value
            .filter(port => Number.isFinite(port.local_port))
            .map(port => port.local_port);
          if (modalPorts.length > 0) {
            const duplicates = modalPorts.some(port => allPorts.includes(port));
            return duplicates;
          }
          return false;
        });

      // -----------------------------------------------
      // Navigation and Page Switching
      // -----------------------------------------------

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

      // -----------------------------------------------
      // Version, Profiles, and Regions Management
      // -----------------------------------------------

        const getVersion = async () => {
          console.debug('Fetching version...');
          data = await apiFetch("/api/version")
          version.value = data.version;
          title.value = data.name;
          operating_system.value = data.operating_system;
          console.log('Version:', version.value);
        };

        const sessionsTableColumns = ref([
          { title: 'Session Name', field: 'name' },
          { title: 'SSO Start URL', field: 'sso_start_url' },
          { title: 'SSO Region', field: 'sso_region' },
          { title: 'SSO Registration Scopes', field: 'sso_registration_scopes' }
        ]);

        const getSessions = async () => {
          console.debug('Fetching sessions...');
          data = await apiFetch("/api/config/sessions");
          sessions.value = data;
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
          data = await apiFetch("/api/profiles")
          profiles.value = data;
        };

        const getRegionsAll = async () => {
          console.debug('Fetching all regions...');
          data = await apiFetch("/api/regions/all")
          regionsAll.value = data;
        };

        const getRegionsSelected = async () => {
          console.debug('Fetching selected regions...');
          data = await apiFetch("/api/regions")
          regionsSelected.value = data;
        };

      // -----------------------------------------------
      // Preferences Management
      // -----------------------------------------------

        const getPreferences = async () => {
          console.debug('Fetching preferences...');
          data = await apiFetch("/api/preferences")
          preferences.value = data;

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

          data = await apiFetch("/api/preferences", {
            method: 'POST',
            body: JSON.stringify(newPreferences)
          })
          console.debug('Preferences saved successfully:', data);
          await getPreferences();
          toast('Preferences saved successfully', 'success');
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
          return validPortStart && validPortEnd && validPortRange;
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
      // Instance scanning and connection management
      // -----------------------------------------------

        const connect = async () => {
          console.debug('Connecting to AWS...');
          isConnecting.value = true;
          data = await apiFetch("/api/connect", {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value
            })
          });
          currentAccountId.value = data.account_id;
          await getInstances();
          isConnecting.value = false;
          toast('Connected to AWS successfully', 'success');
        };

        const disconnect = async (connection_id) => {
          console.debug('Terminating connection:', connection_id);
          data = await apiFetch(`/api/terminate-connection/${connection_id}`, {
            method: 'POST'
          });
          await getActiveConnections();
          toast('Connection terminated successfully', 'warning');
        };

        const getActiveConnections = async () => {
          data = await apiFetch("/api/active-connections");
          activeConnectionsCount.value = data.length;
          activeConnections.value = data;
        };

        const instancesTableColumns = ref([
          { title: 'Name', field: 'name' },
          { title: 'Instance ID', field: 'id' },
          { title: 'OS', field: 'os' },
          { title: 'Type', field: 'type' }
        ]);

        const getInstances = async () => {
          console.debug('Fetching instances...');
          data = await apiFetch("/api/instances");
          instances.value = data;
          instancesDetails[instances.value.id] = {};
          instancesCount.value = instances.value.length;
          toast(`Successfully discovered ${instancesCount.value} instances`, 'success');
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
          data = await apiFetch(`/api/instance-details/${instanceId}`);
          instancesDetails.value[instanceId] = data;
        };

      // -----------------------------------------------
      // Connection Actions
      // -----------------------------------------------

        const startShell = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Starting shell for:', instanceName);
          data = await apiFetch(`/api/shell/${instanceId}`, {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          });
          console.debug('Shell started:', data);
          await getActiveConnections();
          toast('Successfully started shell', 'success');
        };

        const startRdp = async (instanceId, name) => {
          const instanceName = name || instanceId;
          console.debug('Starting RDP for:', instanceName);
          data = await apiFetch(`/api/rdp/${instanceId}`, {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          });
          console.debug('RDP started:', data);
          await getActiveConnections();
          toast('Successfully started RDP', 'success');
        };

        const startPortForwarding = async () => {
          console.debug('Starting port forwarding...');
          portForwardingStarting.value = true;

          data = await apiFetch(`/api/custom-port/${portForwardingModalProperties.value.instanceId}`, {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: portForwardingModalProperties.value.instanceName,
              mode: portForwardingModalProperties.value.mode,
              remote_port: portForwardingModalProperties.value.remotePort,
              remote_host: portForwardingModalProperties.value.remoteHost,
              username: portForwardingModalProperties.value.username
            })
          });
          console.debug('Port forwarding started:', data);
          toast('Successfully started port forwarding', 'success');

          if (portForwardingModalProperties.value.username && data.local_port) {
            await addWindowsCredential(
              portForwardingModalProperties.value.instanceId,
              portForwardingModalProperties.value.instanceName,
              portForwardingModalProperties.value.username,
              data.local_port
            );
          }
          await getActiveConnections();

          portForwardingModal.value.hide();
          portForwardingStarting.value = false;
        };

        const addWindowsCredential = async (instanceId, instanceName, username, localPort) => {
          console.debug(`Adding Windows credential for ${instanceName} (${instanceId})`);
          await fetch(`/api/config/credential`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              instance_name: instanceName,
              instance_id: instanceId,
              username: username,
              local_port: localPort
            })
          })
          .then((response) => response.json())
          .then((data) => {
            if (!data.status || data.status !== 'success') {
              throw new Error(data.message || 'Unknown error');
            }
            console.debug('Windows credential added successfully:', data);
            toast('Windows credential added successfully', 'success');
          })
          .catch((error) => {
            console.error('Error adding Windows credential:', error);
            toast('Error adding Windows credential', 'danger');
          });
        };

        const deleteWindowsCredential = async (instanceId, instanceName, localPort) => {
          console.debug(`Deleting Windows credential for ${instanceName} (${instanceId}) on port ${localPort}`);
          await fetch(`/api/config/credential`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              instance_name: instanceName,
              instance_id: instanceId,
              local_port: localPort
            })
          })
          .then((response) => response.json())
          .then((data) => {
            if (!data.status || data.status !== 'success') {
              throw new Error(data.message || 'Unknown error');
            }
            console.debug('Windows credential deleted successfully:', data);
            toast('Windows credential deleted successfully', 'success');
          })
          .catch((error) => {
            console.error('Error deleting Windows credential:', error);
            toast('Error deleting Windows credential', 'danger');
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
              throw new Error(data.message || 'Unknown error');
            }
            await getActiveConnections();
            toast('Successfully opened RDP client', 'success');
          })
          .catch((error) => {
            console.error('Error opening RDP client:', error);
            toast('Error opening RDP client', 'danger');
          });
        };

      // -----------------------------------------------
      // Modals
      // -----------------------------------------------

        const showPortForwardingModal = async (instanceId, name) => {
          portForwardingModal.value = new bootstrap.Modal(document.getElementById('portForwardingModal'), {
            keyboard: true
          });
          document.getElementById('portForwardingModal').addEventListener('hidden.bs.modal', () => {
            portForwardingModalProperties.value = {};
            portForwardingStarting.value = false;
          });
          portForwardingModalProperties.value = {
            instanceId: instanceId,
            instanceName: name,
            mode: 'local',
            remotePort: 1433,
            remoteHost: '',
            username: ''
          };
          portForwardingModal.value.show();
        };

        const showPortMappingsModal = async (instanceId, name) => {
          const instanceName = name || instanceId;
          portMappingsModal.value = new bootstrap.Modal(document.getElementById('portMappingsModal'), {
            keyboard: true
          });
          document.getElementById('portMappingsModal').addEventListener('hidden.bs.modal', () => {
            portMappingsModalInstance.value = null;
            portMappingsModalProperties.value = [];
            await getPreferences();
          });
          portMappingsModalInstance.value = { id: instanceId, name: name };
          portMappingsModalProperties.value = portMappings.value[instanceName] || [];
          portMappingsModal.value.show();
        };

        const savePortMappings = async (instanceId, name) => {
          const instanceName = name || instanceId;
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
            await getPreferences();
            console.debug('Port mappings saved successfully:', data);
            toast('Port mappings saved successfully', 'success');
          })
          .catch((error) => {
            console.error('Error saving port mappings:', error)
            toast('Error saving port mappings', 'danger');
          });
          portMappingsModal.value.hide();
        };

        const addPortMapping = () => {
          portMappingsModalProperties.value.push({
            local_port: '',
            remote_port: ''
          });
        };

        const removePortMapping = (index) => {
          portMappingsModalProperties.value.splice(index, 1);
        };

        const showAddSessionModal = async (instanceId, name) => {
          addSessionModal.value = new bootstrap.Modal(document.getElementById('addSessionModal'), {
            keyboard: true
          });
          document.getElementById('addSessionModal').addEventListener('hidden.bs.modal', () => {
            addSessionModalProperties.value = {};
          });
          addSessionModalProperties.value = {
            name: '',
            sso_start_url: '',
            sso_region: '',
            sso_registration_scopes: ''
          };
          addSessionModal.value.show();
        };

        const addSession = async () => {
          console.debug('Adding new session...');
          data = await apiFetch("/api/config/session", {
            method: 'POST',
            body: JSON.stringify(addSessionModalProperties.value)
          })
          await getSessions();
          addSessionModal.value.hide();          
          toast('Session added successfully', 'success');
        };

        const deleteSession = async (sessionName) => {
          console.debug('Deleting session:', sessionName);
          data = await apiFetch(`/api/config/session/${sessionName}`, {
            method: 'DELETE'
          })
          await getSessions();
          toast('Session deleted successfully', 'success');          
        };

        const showAddProfileModal = async (instanceId, name) => {
          addProfileModal.value = new bootstrap.Modal(document.getElementById('addProfileModal'), {
            keyboard: true
          });
          document.getElementById('addProfileModal').addEventListener('hidden.bs.modal', () => {
            addProfileModalProperties.value = {};
          });
          addProfileModalProperties.value = {
            name: '',
            region: '',
            sso_account_id: '',
            sso_role_name: '',
            sso_session: '',
            output: 'json'
          };
          addProfileModal.value.show();
        };

        const addProfile = async () => {
          console.debug('Adding new profile...');
          data = await apiFetch("/api/config/profile", {
            method: 'POST',
            body: JSON.stringify(addProfileModalProperties.value)
          })
          await getProfiles();
          addProfileModal.value.hide();
          toast('Profile added successfully', 'success');
        };

        const deleteProfile = async (profileName) => {
          console.debug('Deleting profile:', profileName);
          data = await apiFetch(`/api/config/profile/${profileName}`, {
            method: 'DELETE'
          })
          await getProfiles();
          toast('Profile deleted successfully', 'success');
        };

      // -----------------------------------------------
      // Event Listeners
      // -----------------------------------------------

        watch(currentProfile, (newProfile) => {
          localStorage.setItem('lastProfile', newProfile);
        });

        watch(currentRegion, (newRegion) => {
          localStorage.setItem('lastRegion', newRegion);
        });

      // -----------------------------------------------
      // Utility Functions
      // -----------------------------------------------

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

      // -----------------------------------------------
      // Check GitHub for updates
      // -----------------------------------------------
        const checkForUpdates = async () => {
          console.debug('Checking for updates...');
          data = await apiFetch("https://api.github.com/repos/napalm255/ssm-manager/releases/latest");
          const currentVersion = `v${version.value}`;
          const githubVersion = data.tag_name;
          const githubUrl = data.html_url;

          if (!githubVersion || !githubUrl) {
            toast('Failed querying for version', 'danger');
            new Error('Failed querying for version');
          } else if (githubVersion !== currentVersion) {
            console.debug('New version available:', githubVersion);
            toast(`New version available: <b><a href="${githubUrl}" target="_blank">${githubVersion}</a></b>`, 'info');
          } else {
            console.debug('No updates available');
            toast('You are using the latest version', 'success');
          }
        };

      // -----------------------------------------------
      // API Handler
      // -----------------------------------------------
        const apiFetch = async (url, options = {}) => {
          try {
            if (!options.method) {
              options.method = 'GET';
            }

            if (options.method == 'POST' && !options.headers) {
              options.headers = {
                'Content-Type': 'application/json'
              };
            }

            const response = await fetch(url, options);
            const data = await response.json();
            if (options.method !== 'GET' && (data.status && data.status !== 'success' && data.status !== 'active')) {
              toast(data.message || 'Unknown error', 'danger');
              throw new Error(data.message || 'Unknown error');
            }
            return data;
          } catch (error) {
            throw error; // Re-throw the error for further handling if needed
          }
        };

      // -----------------------------------------------
      // Data Refresh
      // -----------------------------------------------

        const dataRefresh = async () => {
          console.debug('Refreshing data...');
          await getVersion();
          await getSessions();
          await getProfiles();
          await getRegionsAll();
          await getRegionsSelected();
          await getPreferences();
        };

      // -----------------------------------------------
      // Lifecycle Hooks
      // -----------------------------------------------

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
          await getVersion();
          checkForUpdates();
          getSessions();
          getProfiles();
          getRegionsAll();
          getRegionsSelected();
          await getPreferences();

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
          title, version, operating_system, githubUrl, navBar, switchPage, currentPage, currentHash, themeToggle, toast, copyToClipboard, timeAgo,
          hideTooltip, tooltipTriggerList, tooltipList,
          preferences, getPreferences, savePreferences, prefPortStart, prefPortEnd, prefPortCount, prefLogLevel, prefRegions, prefRegionsCount, prefCredentials, prefCredentialsCount, portMappings,
          regionsSelected, regionsAll, currentProfile, currentRegion, currentAccountId,
          sessions, addSession, deleteSession, sessionsCount, sessionsTableColumns, showAddSessionModal, addSessionModalProperties,
          profiles, addProfile, deleteProfile, profilesCount, profilesTableColumns, showAddProfileModal, addProfileModalProperties,
          addCredential, removeCredential,
          showPortForwardingModal, portForwardingModalProperties, portForwardingStarting,
          showPortMappingsModal, portMappingsModalInstance, portMappingsModalProperties, savePortMappings, addPortMapping, removePortMapping, portMappingsModalDuplicatePort,
          connect, disconnect, isConnecting, startShell, startRdp, openRdpClient, startPortForwarding,
          getInstances, getInstanceDetails, instances, instancesCount, instancesTableColumns, instancesDetails, instanceDetailsColumns,
          activeConnections, activeConnectionsCount,
        };
    }
});
app.mount("#app");
