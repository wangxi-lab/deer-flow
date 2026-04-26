import {
  DEFAULT_LOCAL_SETTINGS,
  LOCAL_SETTINGS_KEY,
  THREAD_MODEL_KEY_PREFIX,
  THREAD_RAG_RESOURCES_KEY_PREFIX,
  THREAD_SELECTED_SKILLS_KEY_PREFIX,
  getLocalSettings,
  getThreadModelName,
  getThreadRAGResourceIds,
  getThreadSelectedSkillNames,
  saveLocalSettings,
  saveThreadModelName,
  saveThreadRAGResourceIds,
  saveThreadSelectedSkillNames,
  type LocalSettings,
} from "./local";

type Listener = () => void;

export type LocalSettingsSetter = <K extends keyof LocalSettings>(
  key: K,
  value: Partial<LocalSettings[K]>,
) => void;

const listeners = new Set<Listener>();
const threadModelNames = new Map<string, string | undefined>();
const threadRagResourceIds = new Map<string, string[] | undefined>();
const threadSelectedSkillNames = new Map<string, string[] | undefined>();

let baseSettings: LocalSettings = DEFAULT_LOCAL_SETTINGS;
let baseSettingsLoaded = false;
let storageListenerRegistered = false;

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

function ensureBaseSettingsLoaded() {
  if (baseSettingsLoaded || typeof window === "undefined") {
    return;
  }

  baseSettings = getLocalSettings();
  baseSettingsLoaded = true;
}

function ensureStorageListenerRegistered() {
  if (storageListenerRegistered || typeof window === "undefined") {
    return;
  }

  window.addEventListener("storage", handleStorage);
  storageListenerRegistered = true;
}

function mergeSettingsSection<K extends keyof LocalSettings>(
  settings: LocalSettings,
  key: K,
  value: Partial<LocalSettings[K]>,
): LocalSettings {
  return {
    ...settings,
    [key]: {
      ...settings[key],
      ...value,
    },
  } as LocalSettings;
}

function handleStorage(event: StorageEvent) {
  if (event.storageArea && event.storageArea !== localStorage) {
    return;
  }

  ensureBaseSettingsLoaded();

  if (event.key === null) {
    baseSettings = getLocalSettings();
    threadModelNames.clear();
    threadRagResourceIds.clear();
    threadSelectedSkillNames.clear();
    emitChange();
    return;
  }

  if (event.key === LOCAL_SETTINGS_KEY) {
    baseSettings = getLocalSettings();
    emitChange();
    return;
  }

  if (!event.key.startsWith(THREAD_MODEL_KEY_PREFIX)) {
    if (event.key.startsWith(THREAD_RAG_RESOURCES_KEY_PREFIX)) {
      const threadId = event.key.slice(THREAD_RAG_RESOURCES_KEY_PREFIX.length);
      threadRagResourceIds.set(threadId, getThreadRAGResourceIds(threadId));
      emitChange();
      return;
    }
    if (event.key.startsWith(THREAD_SELECTED_SKILLS_KEY_PREFIX)) {
      const threadId = event.key.slice(THREAD_SELECTED_SKILLS_KEY_PREFIX.length);
      threadSelectedSkillNames.set(
        threadId,
        getThreadSelectedSkillNames(threadId),
      );
      emitChange();
    }
    return;
  }

  const threadId = event.key.slice(THREAD_MODEL_KEY_PREFIX.length);
  threadModelNames.set(threadId, getThreadModelName(threadId));
  emitChange();
}

export function subscribe(listener: Listener): () => void {
  ensureBaseSettingsLoaded();
  ensureStorageListenerRegistered();
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function getBaseSettingsSnapshot(): LocalSettings {
  ensureBaseSettingsLoaded();
  return baseSettings;
}

export function getThreadModelSnapshot(threadId: string): string | undefined {
  ensureBaseSettingsLoaded();

  if (!threadModelNames.has(threadId)) {
    threadModelNames.set(threadId, getThreadModelName(threadId));
  }

  return threadModelNames.get(threadId);
}

export function getThreadRAGResourceIdsSnapshot(
  threadId: string,
): string[] | undefined {
  ensureBaseSettingsLoaded();

  if (!threadRagResourceIds.has(threadId)) {
    threadRagResourceIds.set(threadId, getThreadRAGResourceIds(threadId));
  }

  return threadRagResourceIds.get(threadId);
}

export function getThreadSelectedSkillNamesSnapshot(
  threadId: string,
): string[] | undefined {
  ensureBaseSettingsLoaded();

  if (!threadSelectedSkillNames.has(threadId)) {
    threadSelectedSkillNames.set(threadId, getThreadSelectedSkillNames(threadId));
  }

  return threadSelectedSkillNames.get(threadId);
}

export const updateLocalSettings: LocalSettingsSetter = (key, value) => {
  ensureBaseSettingsLoaded();
  ensureStorageListenerRegistered();

  baseSettings = mergeSettingsSection(baseSettings, key, value);
  saveLocalSettings(baseSettings);
  emitChange();
};

export function updateThreadSettings<K extends keyof LocalSettings>(
  threadId: string,
  key: K,
  value: Partial<LocalSettings[K]>,
) {
  ensureBaseSettingsLoaded();
  ensureStorageListenerRegistered();

  const nextBaseSettings = mergeSettingsSection(baseSettings, key, value);
  baseSettings = nextBaseSettings;
  saveLocalSettings(baseSettings);

  if (
    key === "context" &&
    Object.prototype.hasOwnProperty.call(value, "model_name")
  ) {
    const contextValue = value as Partial<LocalSettings["context"]>;
    const threadModelName = contextValue.model_name;
    threadModelNames.set(threadId, threadModelName);
    saveThreadModelName(threadId, threadModelName);
  }

  if (
    key === "context" &&
    Object.prototype.hasOwnProperty.call(value, "rag_resource_ids")
  ) {
    const contextValue = value as Partial<LocalSettings["context"]>;
    const resourceIds = contextValue.rag_resource_ids;
    threadRagResourceIds.set(threadId, resourceIds);
    saveThreadRAGResourceIds(threadId, resourceIds);
  }

  if (
    key === "context" &&
    Object.prototype.hasOwnProperty.call(value, "selected_skill_names")
  ) {
    const contextValue = value as Partial<LocalSettings["context"]>;
    const skillNames = contextValue.selected_skill_names;
    threadSelectedSkillNames.set(threadId, skillNames);
    saveThreadSelectedSkillNames(threadId, skillNames);
  }

  emitChange();
}
