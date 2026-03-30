### The Precise Step-by-Step Guide: "The Japan Engine"

This setup allows you to input `2026-02-02T09:00:00` (Monday morning) and get a millisecond-perfect route based on official train timetables.

#### **Prerequisites**
1.  **Server/Computer:** You need **RAM**.
    *   *Tokyo Only:* 4GB - 8GB RAM.
    *   *All of Japan:* 32GB+ RAM (It is a massive graph).
    *   *Recommendation:* Start with just the "Kanto" (Tokyo) region to test.
2.  **Java:** You need **Java 21** (LTS) installed.
    *   Check with: `java -version`

#### **Step 1: Create the Workspace**
Create the workspace the launchers expect and keep the source data in separate folders:

```bash
mkdir -p otp-routing/assets otp-routing/gtfs_backup
cd otp-routing
```

#### **Step 2: Download the Engine (OTP)**
We will use **OpenTripPlanner v2**.
1.  Go to the [OpenTripPlanner releases page](https://github.com/opentripplanner/OpenTripPlanner/releases).
2.  Download a shaded release JAR (`*-shaded.jar`).
3.  Rename the file to `otp.jar`.
4.  Save it at `otp-routing/assets/otp.jar`.

The launchers and helper scripts look for that exact path.

#### **Step 3: Download the Map (OSM)**
We need the street network for the biking/walking part.
1.  Go to the [Geofabrik Japan region page](https://download.geofabrik.de/asia/japan/kanto.html) or another region you want to use.
2.  Download the `.osm.pbf` extract for that region.
3.  Save it in `otp-routing/assets/` with any filename ending in `.osm.pbf`, for example `kanto.osm.pbf`.

The launchers will pick the first `.osm.pbf` file they find in `otp-routing/assets/`.

#### **Step 4: Download the Timetables (GTFS)**
This is the "Secret Sauce." In Japan, this data is standardized as "GTFS-JP."
1.  Register at [ODPT](https://developer.odpt.org/).
2.  Wait for the developer account to be enabled if the site asks you to wait.
3.  Create or copy your API access token from [ODPT edit keys](https://developer.odpt.org/editkeys).
4.  Use that token to download the GTFS `.zip` files you need from [CKAN ODPT datasets](https://ckan.odpt.org/dataset).
    *   Some datasets are public and can be downloaded without a token.
5.  Save the `.zip` files in `otp-routing/gtfs_backup/`.

**Important:** Keep the original archive filename exactly as downloaded. Some feeds are sensitive to the wrong `.zip` name, and renaming them can make OTP fail to recognize them.
*   Do not unzip the archives.
*   The launchers validate the archives and copy the good ones into `otp-routing/assets/` before OTP starts.

#### **Step 5: Configure the Engine**
Create a file named `router-config.json` in the same folder. This tells OTP to enable the "Bike Rental" or specific routing logic. For a basic private bike setup, paste this:

```json
{
  "routingDefaults": {
    "walkSpeed": 1.3,
    "transferSlack": 120,
    "maxWalkDistance": 2000,
    "allowUnknownModes": false
  },
  "updaters": []
}
```
*Note: `transferSlack` adds a 2-minute buffer to train transfers so you don't miss connections.*

#### **Step 6: Build and Run**
Now we "compile" the map and timetables into a graph, then start the server.

**Run this command:**
```bash
cd otp-routing/assets
java -Xmx8G -jar otp.jar --build --serve .
```
*   `-Xmx8G`: Allocates 8GB of RAM. Increase this if you add more cities.
*   `.`: Tells OTP to look in the *current folder* for the `.pbf` and `.zip` files.
*   If you are using the repository launchers, they already copy valid GTFS archives from `otp-routing/gtfs_backup/` into `otp-routing/assets/` for you.

**Wait.**
It will take 2-10 minutes to "Build Graph." You will see logs like `Reading GTFS...` and `Linking transit stops to streets...`.
When you see `Grizzly server running`, it is ready.

### How to Use It (The Alternative API)

You can now query your local API exactly like you would Google's, but with more power.

**Endpoint:**
`http://localhost:8080/otp/routers/default/plan`

**Example Request (Walking + Train):**
*   **fromPlace:** `35.6812,139.7671` (Tokyo Station)
*   **toPlace:** `35.6586,139.7454` (Tokyo Tower)
*   **time:** `09:00`
*   **date:** `2026-02-02` (Your Working Monday)
*   **mode:** `WALK,TRANSIT`
*   **arriveBy:** `true` (Calculates backwards from arrival time)

**Example Request (Bike Only):**
*   **mode:** `BICYCLE`

**Example Request (Bike to Train - The "Commuter Special"):**
*   **mode:** `BICYCLE,TRANSIT`
*   *This will route you on a bike to the station, park the bike, and take the train.*

### Summary of Risks & Tips
1.  **Updates:** Trains in Japan change schedules slightly every March. You must re-download the GTFS zips once a year and restart the server.
2.  **Station Linking:** Sometimes the raw data has the "Station" node slightly disconnected from the "Street" node. OTP usually fixes this automatically, but if you get "Trip not possible," it's often because the map thinks the station entrance is walled off.
3.  **Real-time:** This solution relies on **static timetables**. It will not know if a train is delayed *right now* (GTFS-Realtime is a much harder setup). But for planning a route for "next Monday," it is perfect.