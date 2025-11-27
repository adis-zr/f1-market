import { useState, useCallback, useEffect } from 'react';

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

let toastId = 0;
let toastListeners: Array<(toasts: Toast[]) => void> = [];
let globalToasts: Toast[] = [];

function notifyListeners() {
  toastListeners.forEach((listener) => listener([...globalToasts]));
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>(globalToasts);

  useEffect(() => {
    const listener = (newToasts: Toast[]) => {
      setToasts(newToasts);
    };
    toastListeners.push(listener);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== listener);
    };
  }, []);

  const toast = useCallback(
    ({ title, description, variant = 'default' }: Omit<Toast, 'id'>) => {
      const id = `toast-${toastId++}`;
      const newToast = { id, title, description, variant };
      globalToasts = [...globalToasts, newToast];
      notifyListeners();

      // Auto remove after 5 seconds
      setTimeout(() => {
        globalToasts = globalToasts.filter((t) => t.id !== id);
        notifyListeners();
      }, 5000);
    },
    []
  );

  return { toast, toasts };
}

