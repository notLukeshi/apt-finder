// Commute time thresholds configuration (in minutes)
// These values determine the color coding for commute distances:
// - Green (excellent): <= greenMax
// - Orange (good): > greenMax and <= orangeMax  
// - Red (far): > orangeMax

export const COMMUTE_THRESHOLDS = {
  greenMax: 25,   // Minutes - excellent commute (green)
  orangeMax: 45,  // Minutes - good commute (orange), above this is red
};

// Warning threshold for too many apartments on map - enables clustering
export const MAP_WARNING_THRESHOLD = 300;

export default COMMUTE_THRESHOLDS;
