const { createApp, ref, computed, onMounted, onUnmounted, watch } = Vue;

const app = createApp({
    setup() {
        const title = ref("SSM Manager");
        const version = ref("");
        const operating_system = ref("");
        const githubUrl = ref('https://github.com/napalm255/ssm-manager');

        const currentHash = ref('#/start');
        const currentProfile = ref("");
        const currentRegion = ref("");
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

        const hosts = ref([]);
        const hostsAdding = ref(false);
        const hostsCount = computed(() => {
          return hosts.value.length;
        });
        const addHostModal = ref(null);
        const addHostModalProperties = ref({});

        const tooltipTriggerList = ref([]);
        const tooltipList = ref([]);

        const isConnecting = ref(false);

        const instances = ref([]);
        const instancesTimestamp = ref(null);
        const instancesCount = computed(() => {
          return instances.value.length;
        });
        const instancesDetails = ref({});

        const activeConnections = ref([]);
        const activeConnectionsCount = computed(() => {
          return activeConnections.value.length;
        });
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
              return instance?.ports?.map(port => port.local_port);
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
      // Navigation
      // -----------------------------------------------

        const navBar = ref([
          {'name': 'Home', 'icon': 'bi bi-house-door-fill', 'hash': '#/home'},
          {'name': 'Instances', 'icon': 'bi bi-hdd-rack-fill', 'hash': '#/instances'},
          {'name': 'Preferences', 'icon': 'bi bi-gear-fill', 'hash': '#/preferences'},
          {'name': 'Profiles', 'icon': 'bi bi-person-lines-fill', 'hash': '#/profiles'},
          {'name': 'Hosts File', 'icon': 'bi bi-file-earmark-text', 'hash': '#/hosts'}
        ]);

        const updateHash = async () => {
          currentHash.value = window.location.hash;
          if (!currentHash.value) {
            currentHash.value = '#/start';
          }
          switchPage(currentHash.value);
        }

        const switchPage = async (page) => {
          if (!page || page === '#/start') {
            if (profilesCount.value === 0) {
              page = '#/home';
            } else {
              page = '#/instances';
            }
          }
          const pages = document.querySelectorAll('.page');
          pages.forEach(p => p.style.display = 'none');
          const currentPage = document.getElementById(page.replace('#/', '').toLowerCase());
          currentPage.style.display = 'block';
          localStorage.setItem('lastPage', page);
          currentHash.value = page;
          window.location.hash = page;
        };

      // -----------------------------------------------
      // Table Columns
      // -----------------------------------------------

        const sessionsTableColumns = ref([
          { title: 'Session Name', field: 'name' },
          { title: 'SSO Start URL', field: 'sso_start_url' },
          { title: 'SSO Region', field: 'sso_region' },
          { title: 'SSO Registration Scopes', field: 'sso_registration_scopes' }
        ]);

        const profilesTableColumns = ref([
          { title: 'Profile Name', field: 'name' },
          { title: 'Account ID', field: 'sso_account_id' },
          { title: 'Region', field: 'region' },
          { title: 'Role Name', field: 'sso_role_name' },
          { title: 'Session Name', field: 'sso_session' }
        ]);

        const hostsTableColumns = ref([
          { title: 'IP Address', field: 'ip' },
          { title: 'Hostname', field: 'hostname' }
        ]);

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

      // -----------------------------------------------
      // Version, Profiles, and Regions
      // -----------------------------------------------

        const getVersion = async () => {
          const data = await apiFetch("/api/version");
          version.value = data.version;
          title.value = data.name;
          operating_system.value = data.operating_system;
          console.log('Version:', version.value);
        };

        const getSessions = async () => {
          sessions.value = await apiFetch("/api/config/sessions");
        };

        const getProfiles = async () => {
          profiles.value = await apiFetch("/api/profiles");
        };

        const getRegionsAll = async () => {
          regionsAll.value = await apiFetch("/api/regions/all");
        };

        const getRegionsSelected = async () => {
          regionsSelected.value = await apiFetch("/api/regions");
        };

        const getHosts = async () => {
          hosts.value = await apiFetch("/api/config/hosts");
        }

      // -----------------------------------------------
      // Preferences Management
      // -----------------------------------------------

        const getPreferences = async () => {
          preferences.value = await apiFetch("/api/preferences");

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

          await apiFetch("/api/preferences", {
            method: 'POST',
            body: JSON.stringify(newPreferences)
          })
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
          prefCredentials.value.push({
            'username': '',
            'password': ''
          });
        };

        const removeCredential = (index) => {
          prefCredentialsToDelete.value.push(prefCredentials.value[index]);
          prefCredentials.value.splice(index, 1);
        }

      // -----------------------------------------------
      // Instance scanning and connection management
      // -----------------------------------------------

        const connect = async () => {
          isConnecting.value = true;
          try {
            const data = await apiFetch("/api/connect", {
              method: 'POST',
              body: JSON.stringify({
                profile: currentProfile.value,
                region: currentRegion.value
              })
            });
            currentAccountId.value = data.account_id;
            await getInstances();
            toast('Connected to AWS successfully', 'success');
          } catch (error) {
            console.error('Connection error:', error);
          }
          isConnecting.value = false;
        };

        const disconnect = async (connection_id) => {
          await apiFetch(`/api/terminate-connection/${connection_id}`, {
            method: 'POST'
          });
          await getActiveConnections();
          toast('Connection terminated successfully', 'warning');
        };

        const getActiveConnections = async () => {
          activeConnections.value = await apiFetch("/api/active-connections");
        };

        const getInstances = async () => {
          instances.value = await apiFetch("/api/instances");
          instancesTimestamp.value = Date.now() + 5 * 60 * 1000; // Set timestamp to 5 minutes in the future
          instancesDetails.value[instances.value.id] = {};
          toast(`Successfully discovered ${instancesCount.value} instances`, 'success');
        };

        const getInstanceDetails = async (instanceId) => {
          const data = await apiFetch(`/api/instance-details/${instanceId}`);
          instancesDetails.value[instanceId] = data;
        };

      // -----------------------------------------------
      // Connection Actions
      // -----------------------------------------------

        const startShell = async (instanceId, name) => {
          const instanceName = name || instanceId;
          await apiFetch(`/api/shell/${instanceId}`, {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          });
          await getActiveConnections();
          toast('Successfully started shell', 'success');
        };

        const startRdp = async (instanceId, name) => {
          const instanceName = name || instanceId;
          await apiFetch(`/api/rdp/${instanceId}`, {
            method: 'POST',
            body: JSON.stringify({
              profile: currentProfile.value,
              region: currentRegion.value,
              name: instanceName,
            })
          });
          await getActiveConnections();
          toast('Successfully started RDP', 'success');
        };

        const startPortForwarding = async () => {
          portForwardingStarting.value = true;

          const data = await apiFetch(`/api/custom-port/${portForwardingModalProperties.value.instanceId}`, {
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
          toast('Successfully started port forwarding', 'success');

          if (portForwardingModalProperties.value.username && data.local_port) {
            await addWindowsCredential(
              portForwardingModalProperties.value.instanceId,
              portForwardingModalProperties.value.instanceName,
              portForwardingModalProperties.value.username,
              data.local_port
            );
          }

          if (portForwardingModalProperties.value.hostentry) {
            await portForwardingAddHost();
          }

          await getActiveConnections();
          portForwardingModal.value.hide();
          portForwardingStarting.value = false;
        };

        const addWindowsCredential = async (instanceId, instanceName, username, localPort) => {
          await apiFetch(`/api/config/credential`, {
            method: 'POST',
            body: JSON.stringify({
              instance_name: instanceName,
              instance_id: instanceId,
              username: username,
              local_port: localPort
            })
          });
          toast('Windows credential added successfully', 'success');
        };

        const openRdpClient = async (local_port) => {
          await apiFetch(`/api/rdp/${local_port}`);
          toast('Successfully opened RDP client', 'success');
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

        const portForwardingAddHost = async () => {
          const username = portForwardingModalProperties.value.username || '';
          const domain = ''
          if (username && username.includes('\\')) {
            const parts = username.split('\\');
            if (parts.length > 1) {
              domain = parts[0];
              username = parts[1];
            } else {
              domain = '';
              username = parts[0];
            }
          }
          let hostname = portForwardingModalProperties.value.instanceName;
          hostname += domain ? `.${domain}` : '';

          const newHost = {
            ip: "127.0.0.1",
            hostname: hostname
          };
          await apiFetch("/api/config/host", {
            method: 'POST',
            body: JSON.stringify(newHost)
          });
          await getHosts();
          toast('Host added successfully', 'success');
        };

        const showPortMappingsModal = async (instanceId, name) => {
          const instanceName = name || instanceId;
          portMappingsModal.value = new bootstrap.Modal(document.getElementById('portMappingsModal'), {
            keyboard: true
          });
          document.getElementById('portMappingsModal').addEventListener('hidden.bs.modal', () => {
            portMappingsModalInstance.value = null;
            portMappingsModalProperties.value = [];
            getPreferences();
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

          await apiFetch(`/api/preferences/${instanceName}`, {
            method: 'POST',
            body: JSON.stringify(newMappings)
          })
          getPreferences();
          portMappingsModal.value.hide();
          toast('Port mappings saved successfully', 'success');
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
          document.getElementById('addSessionModal').addEventListener('hidden.bs.modal', async () => {
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
          await apiFetch("/api/config/session", {
            method: 'POST',
            body: JSON.stringify(addSessionModalProperties.value)
          })
          await getSessions();
          addSessionModal.value.hide();
          toast('Session added successfully', 'success');
        };

        const deleteSession = async (sessionName) => {
          await apiFetch(`/api/config/session/${sessionName}`, {
            method: 'DELETE'
          })
          await getSessions();
          toast('Session deleted successfully', 'success');
        };

        const showAddProfileModal = async (instanceId, name) => {
          addProfileModal.value = new bootstrap.Modal(document.getElementById('addProfileModal'), {
            keyboard: true
          });
          document.getElementById('addProfileModal').addEventListener('hidden.bs.modal', async () => {
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
          await apiFetch("/api/config/profile", {
            method: 'POST',
            body: JSON.stringify(addProfileModalProperties.value)
          })
          await getProfiles();
          addProfileModal.value.hide();
          toast('Profile added successfully', 'success');
        };

        const deleteProfile = async (profileName) => {
          await apiFetch(`/api/config/profile/${profileName}`, {
            method: 'DELETE'
          })
          await getProfiles();
          toast('Profile deleted successfully', 'success');
        };

        const showAddHostModal = async () => {
          addHostModal.value = new bootstrap.Modal(document.getElementById('addHostModal'), {
            keyboard: true
          });
          document.getElementById('addHostModal').addEventListener('hidden.bs.modal', async () => {
            addHostModalProperties.value = {};
          });
          addHostModalProperties.value = {
            hostname: '',
            ip: ''
          };
          addHostModal.value.show();
        };

        const addHost = async () => {
          hostsAdding.value = true;
          await apiFetch("/api/config/host", {
            method: 'POST',
            body: JSON.stringify(addHostModalProperties.value)
          });
          await getHosts();
          addHostModal.value.hide();
          addHostModalProperties.value = {};
          toast('Host added successfully', 'success');
          hostsAdding.value = false;
        };

        const deleteHost = async (hostname) => {
          await apiFetch(`/api/config/host/${hostname}`, {
            method: 'DELETE'
          });
          await getHosts();
          toast('Host deleted successfully', 'success');
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

        watch(currentAccountId, (newAccountId) => {
          localStorage.setItem('lastAccountId', newAccountId);
        });

        watch(instances, (newInstances) => {
          localStorage.setItem('lastInstances', JSON.stringify(newInstances));
        });

        watch(instancesTimestamp, (newTimestamp) => {
          localStorage.setItem('lastInstancesTimestamp', newTimestamp);
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

        const compareVersions = async (v1, v2) => {
          const v1Parts = v1.split('.').map(Number);
          const v2Parts = v2.split('.').map(Number);
          const maxLength = Math.max(v1Parts.length, v2Parts.length);
          for (let i = 0; i < maxLength; i++) {
            const part1 = v1Parts[i] || 0;
            const part2 = v2Parts[i] || 0;
            if (part1 > part2) return 1;  // v1 is greater
            if (part1 < part2) return -1;  // v2 is greater
          }
          return 0;  // Versions are equal
        };

        const copyToClipboard = async (text) => {
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
          const data = await apiFetch("https://api.github.com/repos/napalm255/ssm-manager/releases/latest");
          const currentVersion = `v${version.value}`;
          const githubVersion = data.tag_name;
          const githubUrl = data.html_url;
          const versionComparison = await compareVersions(currentVersion, githubVersion);

          if (!githubVersion || !githubUrl) {
            toast('Failed querying for version', 'danger');
            throw new Error('Failed querying for version');
          }
          console.log('Latest version:', githubVersion);
          if (versionComparison < 0) {
            toast(`New version available: <b><a href="${githubUrl}" class="text-white" target="_blank">${githubVersion}</a></b>`, 'primary');
          } else if (versionComparison === 0) {
            toast('You are using the latest version', 'success');
          } else if (versionComparison > 0) {
            toast(`You are using a development version`, 'warning');
          }
        };

      // -----------------------------------------------
      // API Handler
      // -----------------------------------------------

        const apiFetch = async (url, options = {}) => {
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
        };

      // -----------------------------------------------
      // Lifecycle Hooks
      // -----------------------------------------------

        onMounted(async () => {
          // Watch for hash changes
          window.addEventListener('hashchange', updateHash);

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
            await switchPage('#/start');
          }

          // Set profile, region, and account ID
          const lastProfile = localStorage.getItem('lastProfile');
          if (lastProfile) {
            currentProfile.value = lastProfile;
          }
          const lastRegion = localStorage.getItem('lastRegion');
          if (lastRegion) {
            currentRegion.value = lastRegion;
          }

          // Load data from the server
          await getVersion();
          await getProfiles();
          await getRegionsAll();
          await getRegionsSelected();
          await getPreferences();
          getActiveConnections();
          getSessions();
          getHosts();
          checkForUpdates();

          // Restore instances if available and not expired
          const lastInstances = localStorage.getItem('lastInstances');
          const lastInstancesTimestamp = localStorage.getItem('lastInstancesTimestamp');
          const lastAccountId = localStorage.getItem('lastAccountId');
          if (lastInstances && lastInstancesTimestamp) {
            const item = JSON.parse(lastInstances);
            const now = Date.now();
            if (lastInstancesTimestamp > now) {
              currentAccountId.value = lastAccountId || '';
              instances.value = item;
            } else {
              localStorage.removeItem('lastAccountId');
              localStorage.removeItem('lastInstances');
              localStorage.removeItem('lastInstancesTimestamp');
            }
          }

          // Initialize tooltips
          tooltipTriggerList.value = document.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltipList.value = [...tooltipTriggerList.value].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

          // Query active connections every 2 seconds
          setInterval(getActiveConnections, 2500);
        });

        onUnmounted(async () => {
          // Dispose of tooltips
          tooltipList.value.forEach(tooltip => tooltip.dispose());

          // Clear the interval for active connections
          clearInterval(intervalActiveConnections);

          // Clean up event listeners
          window.removeEventListener('hashchange', updateHash);
        });

        return {
          title, version, operating_system, githubUrl, navBar, switchPage, currentHash, themeToggle, toast, copyToClipboard, timeAgo,
          hideTooltip, tooltipTriggerList, tooltipList,
          preferences, getPreferences, savePreferences, prefPortStart, prefPortEnd, prefPortCount, prefLogLevel, prefRegions, prefRegionsCount, prefCredentials, prefCredentialsCount, portMappings,
          regionsSelected, regionsAll, currentProfile, currentRegion, currentAccountId,
          sessions, addSession, deleteSession, sessionsCount, sessionsTableColumns, showAddSessionModal, addSessionModalProperties,
          profiles, addProfile, deleteProfile, profilesCount, profilesTableColumns, showAddProfileModal, addProfileModalProperties,
          hosts, addHost, deleteHost, hostsAdding, hostsCount, hostsTableColumns, showAddHostModal, addHostModalProperties,
          addCredential, removeCredential,
          showPortForwardingModal, portForwardingModalProperties, portForwardingStarting,
          showPortMappingsModal, portMappingsModalInstance, portMappingsModalProperties, savePortMappings, addPortMapping, removePortMapping, portMappingsModalDuplicatePort,
          connect, disconnect, isConnecting, startShell, startRdp, openRdpClient, startPortForwarding,
          getInstances, getInstanceDetails, instances, instancesCount, instancesDetails, instanceDetailsColumns,
          activeConnections, activeConnectionsCount,
        };
    }
});
app.mount("#app");
