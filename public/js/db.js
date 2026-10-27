/**
 * Goalie Athlete Storage Engine (IndexedDB)
 * High-performance, offline-first persistence for endurance telemetry, workouts, and macrocycles.
 * Eliminates localStorage 5MB quota restrictions.
 */
const GoalieDB = {
    DB_NAME: 'GoalieAthleteDB',
    DB_VERSION: 1,
    db: null,

    async init() {
        if (this.db) return this.db;
        return new Promise((resolve, reject) => {
            if (!('indexedDB' in window)) {
                console.warn('[GoalieDB] IndexedDB not available in this environment. Falling back to memory/local.');
                resolve(null);
                return;
            }

            const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

            request.onupgradeneeded = (e) => {
                const db = e.target.result;

                // 1. Workouts store
                if (!db.objectStoreNames.contains('workouts')) {
                    const ws = db.createObjectStore('workouts', { keyPath: 'id' });
                    ws.createIndex('date', 'date', { unique: false });
                    ws.createIndex('sport_type', 'sport_type', { unique: false });
                    ws.createIndex('created_at', 'created_at', { unique: false });
                }

                // 2. High-density telemetry streams (GPS, second-by-second HR, Power, Cadence)
                if (!db.objectStoreNames.contains('telemetry_streams')) {
                    db.createObjectStore('telemetry_streams', { keyPath: 'activity_id' });
                }

                // 3. Training Macrocycles & Plans
                if (!db.objectStoreNames.contains('plans')) {
                    db.createObjectStore('plans', { keyPath: 'plan_id' });
                }

                // 4. Offline sync queue
                if (!db.objectStoreNames.contains('offline_queue')) {
                    const oq = db.createObjectStore('offline_queue', { keyPath: 'id', autoIncrement: true });
                    oq.createIndex('created_at', 'created_at', { unique: false });
                }
            };

            request.onsuccess = (e) => {
                this.db = e.target.result;
                console.log('[GoalieDB] IndexedDB initialized successfully.');
                resolve(this.db);
            };

            request.onerror = (e) => {
                console.error('[GoalieDB] Initialization error:', e.target.error);
                reject(e.target.error);
            };
        });
    },

    async getStore(storeName, mode = 'readonly') {
        const db = await this.init();
        if (!db) return null;
        const tx = db.transaction(storeName, mode);
        return tx.objectStore(storeName);
    },

    // Workouts API
    async saveWorkout(workout) {
        try {
            const store = await this.getStore('workouts', 'readwrite');
            if (!store) return false;
            if (!workout.id) workout.id = `wk_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
            if (!workout.created_at) workout.created_at = new Date().toISOString();

            return new Promise((resolve, reject) => {
                const req = store.put(workout);
                req.onsuccess = () => resolve(workout);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] saveWorkout error:', err);
            return null;
        }
    },

    async getAllWorkouts() {
        try {
            const store = await this.getStore('workouts', 'readonly');
            if (!store) return [];
            return new Promise((resolve, reject) => {
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] getAllWorkouts error:', err);
            return [];
        }
    },

    async deleteWorkout(id) {
        try {
            const store = await this.getStore('workouts', 'readwrite');
            if (!store) return false;
            return new Promise((resolve, reject) => {
                const req = store.delete(id);
                req.onsuccess = () => resolve(true);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] deleteWorkout error:', err);
            return false;
        }
    },

    // Telemetry Streams API (For high-frequency sensor streams)
    async saveTelemetryStream(activityId, streamData) {
        try {
            const store = await this.getStore('telemetry_streams', 'readwrite');
            if (!store) return false;
            const record = {
                activity_id: activityId,
                updated_at: new Date().toISOString(),
                stream: streamData
            };
            return new Promise((resolve, reject) => {
                const req = store.put(record);
                req.onsuccess = () => resolve(true);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] saveTelemetryStream error:', err);
            return false;
        }
    },

    async getTelemetryStream(activityId) {
        try {
            const store = await this.getStore('telemetry_streams', 'readonly');
            if (!store) return null;
            return new Promise((resolve, reject) => {
                const req = store.get(activityId);
                req.onsuccess = () => resolve(req.result ? req.result.stream : null);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] getTelemetryStream error:', err);
            return null;
        }
    },

    // Plans API
    async savePlan(plan) {
        try {
            const store = await this.getStore('plans', 'readwrite');
            if (!store) return false;
            if (!plan.plan_id) plan.plan_id = `plan_${Date.now()}`;
            plan.saved_at = new Date().toISOString();
            return new Promise((resolve, reject) => {
                const req = store.put(plan);
                req.onsuccess = () => resolve(plan);
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] savePlan error:', err);
            return null;
        }
    },

    async getLatestPlan() {
        try {
            const store = await this.getStore('plans', 'readonly');
            if (!store) return null;
            return new Promise((resolve, reject) => {
                const req = store.getAll();
                req.onsuccess = () => {
                    const plans = req.result || [];
                    if (plans.length === 0) return resolve(null);
                    plans.sort((a, b) => new Date(b.saved_at || 0) - new Date(a.saved_at || 0));
                    resolve(plans[0]);
                };
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] getLatestPlan error:', err);
            return null;
        }
    },

    // Offline Queue API (Auto-sync when back online)
    async queueOfflineAction(url, method, payload) {
        try {
            const store = await this.getStore('offline_queue', 'readwrite');
            if (!store) return false;
            const item = {
                url,
                method,
                payload,
                created_at: new Date().toISOString()
            };
            return new Promise((resolve, reject) => {
                const req = store.add(item);
                req.onsuccess = () => {
                    console.log('[GoalieDB] Queued offline sync item:', item);
                    resolve(req.result);
                };
                req.onerror = () => reject(req.error);
            });
        } catch (err) {
            console.error('[GoalieDB] queueOfflineAction error:', err);
            return null;
        }
    },

    async flushOfflineQueue(getAuthHeaders) {
        if (!navigator.onLine) return 0;
        try {
            const store = await this.getStore('offline_queue', 'readwrite');
            if (!store) return 0;

            const allItems = await new Promise((resolve) => {
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => resolve([]);
            });

            if (allItems.length === 0) return 0;
            console.log(`[GoalieDB] Flushing ${allItems.length} queued offline actions...`);

            let synced = 0;
            for (const item of allItems) {
                try {
                    const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
                    const res = await fetch(item.url, {
                        method: item.method,
                        headers,
                        body: item.payload ? JSON.stringify(item.payload) : undefined
                    });
                    if (res.ok) {
                        const delStore = await this.getStore('offline_queue', 'readwrite');
                        delStore.delete(item.id);
                        synced++;
                    }
                } catch (e) {
                    console.warn('[GoalieDB] Sync attempt failed for item:', item.id, e);
                }
            }
            return synced;
        } catch (err) {
            console.error('[GoalieDB] flushOfflineQueue error:', err);
            return 0;
        }
    }
};

// Auto-initialize GoalieDB when window loads
if (typeof window !== 'undefined') {
    window.GoalieDB = GoalieDB;
    window.addEventListener('DOMContentLoaded', () => GoalieDB.init());
    window.addEventListener('online', async () => {
        if (typeof getAuthHeaders === 'function') {
            const count = await GoalieDB.flushOfflineQueue(getAuthHeaders);
            if (count > 0 && typeof toast !== 'undefined') {
                toast.success('Offline Sync Complete', `${count} recorded workouts synced to server.`);
            }
        }
    });
}
