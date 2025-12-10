import { cn } from '@/lib/utils';
import { useToast } from '@/hooks';

export function ToastContainer() {
  const { toasts } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} />
      ))}
    </div>
  );
}

function Toast({ toast }: { toast: { id: string; title: string; description?: string; variant?: 'default' | 'destructive' } }) {
  return (
    <div
      className={cn(
        'flex items-center gap-4 rounded-lg border p-4 shadow-lg',
        toast.variant === 'destructive'
          ? 'border-destructive bg-destructive text-destructive-foreground'
          : 'bg-background'
      )}
    >
      <div className="flex-1">
        <div className="font-semibold">{toast.title}</div>
        {toast.description && (
          <div className="text-sm opacity-90">{toast.description}</div>
        )}
      </div>
    </div>
  );
}

