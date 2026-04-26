import { useCallback, useMemo, useSyncExternalStore } from "react";

import {
  DEFAULT_LOCAL_SETTINGS,
  applyThreadContextOverrides,
  type LocalSettings,
} from "./local";
import {
  getBaseSettingsSnapshot,
  getThreadModelSnapshot,
  getThreadRAGResourceIdsSnapshot,
  getThreadSelectedSkillNamesSnapshot,
  subscribe,
  updateLocalSettings,
  updateThreadSettings,
  type LocalSettingsSetter,
} from "./store";

export function useLocalSettings(): [LocalSettings, LocalSettingsSetter] {
  const settings = useSyncExternalStore(
    subscribe,
    getBaseSettingsSnapshot,
    () => DEFAULT_LOCAL_SETTINGS,
  );

  const setSettings = useCallback<LocalSettingsSetter>((key, value) => {
    updateLocalSettings(key, value);
  }, []);

  return [settings, setSettings];
}

export function useThreadSettings(
  threadId: string,
): [LocalSettings, LocalSettingsSetter] {
  const baseSettings = useSyncExternalStore(
    subscribe,
    getBaseSettingsSnapshot,
    () => DEFAULT_LOCAL_SETTINGS,
  );

  const threadModelName = useSyncExternalStore(
    subscribe,
    () => getThreadModelSnapshot(threadId),
    () => undefined,
  );

  const threadRAGResourceIds = useSyncExternalStore(
    subscribe,
    () => getThreadRAGResourceIdsSnapshot(threadId),
    () => undefined,
  );

  const threadSelectedSkillNames = useSyncExternalStore(
    subscribe,
    () => getThreadSelectedSkillNamesSnapshot(threadId),
    () => undefined,
  );

  const settings = useMemo(
    () =>
      applyThreadContextOverrides(
        baseSettings,
        threadModelName,
        threadRAGResourceIds,
        threadSelectedSkillNames,
      ),
    [baseSettings, threadModelName, threadRAGResourceIds, threadSelectedSkillNames],
  );

  const setSettings = useCallback<LocalSettingsSetter>(
    (key, value) => {
      updateThreadSettings(threadId, key, value);
    },
    [threadId],
  );

  return [settings, setSettings];
}
