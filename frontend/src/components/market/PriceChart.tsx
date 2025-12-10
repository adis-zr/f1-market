import { usePriceHistory } from '@/hooks';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatPrice, formatDateTime } from '@/lib/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PriceChartProps {
  marketId: number;
}

export function PriceChart({ marketId }: PriceChartProps) {
  const { data: priceHistory, isLoading } = usePriceHistory(marketId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            Loading chart data...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!priceHistory || priceHistory.history.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            No price history available
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare data for chart (reverse to show chronological order)
  const chartData = [...priceHistory.history]
    .reverse()
    .map((entry) => ({
      timestamp: new Date(entry.timestamp).getTime(),
      price: parseFloat(entry.price.toString()),
      timeLabel: formatDateTime(entry.timestamp),
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price History</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                });
              }}
            />
            <YAxis
              tickFormatter={(value) => formatPrice(value)}
            />
            <Tooltip
              formatter={(value: number) => formatPrice(value)}
              labelFormatter={(label) => {
                const date = new Date(label);
                return formatDateTime(date.toISOString());
              }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

