// Set to the machine running the FastAPI server, e.g. 'http://192.168.1.50:8000'.
// Empty host falls back to the same host the page was served from.
export const environment = {
  apiUrl: `http://${window.location.hostname}:8000`,
};
