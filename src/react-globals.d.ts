// Minimal React ambient types for LSP navigation.
// NOT full React types — just enough for hover/go-to-definition
// in a zero-dependency concatenated project.

declare function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void];
declare function useState<T = undefined>(): [T | undefined, (value: T | ((prev: T) => T)) => void];

declare function useRef<T>(initialValue: T): { current: T };
declare function useRef<T = undefined>(): { current: T | undefined };

declare function useEffect(effect: () => (void | (() => void)), deps?: any[]): void;

declare function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;

declare function createPortal(children: any, container: Element): any;
