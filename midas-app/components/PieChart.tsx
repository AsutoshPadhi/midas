import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

export type PieSlice = {
  label: string;
  value: number;
  color: string;
};

type Props = {
  slices: PieSlice[];
  size?: number;
  onSlicePress?: (label: string, value: number) => void;
  selectedSlice?: string;
};

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function wedgePath(cx: number, cy: number, r: number, startAngle: number, sweepAngle: number): string {
  if (sweepAngle >= 359.99) {
    const top = polarToCartesian(cx, cy, r, 0);
    const bot = polarToCartesian(cx, cy, r, 180);
    return `M ${top.x} ${top.y} A ${r} ${r} 0 1 1 ${bot.x} ${bot.y} A ${r} ${r} 0 1 1 ${top.x} ${top.y} Z`;
  }
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, startAngle + sweepAngle);
  const largeArc = sweepAngle > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y} Z`;
}

function getSliceAtAngle(angle: number, slices: PieSlice[]): PieSlice | null {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  let cursor = 0;
  for (const slice of slices) {
    const sweep = (slice.value / total) * 360;
    if (angle >= cursor && angle < cursor + sweep) {
      return slice;
    }
    cursor += sweep;
  }
  return null;
}

export function PieChart({ slices, size = 220, onSlicePress, selectedSlice }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 6;
  const total = slices.reduce((sum, s) => sum + s.value, 0);

  let cursor = 0;
  const wedges = slices.map((slice) => {
    const sweep = (slice.value / total) * 360;
    const path = wedgePath(cx, cy, r, cursor, sweep);
    const isSelected = selectedSlice === slice.label;
    const opacity = isSelected ? 1 : 0.7;
    cursor += sweep;
    return { ...slice, path, isSelected, opacity };
  });

  const handleClick = (e: any) => {
    // Get coordinates relative to the SVG container
    const rect = e.currentTarget?.getBoundingClientRect?.();
    if (!rect) return;
    
    const x = e.nativeEvent?.pageX ?? e.pageX;
    const y = e.nativeEvent?.pageY ?? e.pageY;
    
    if (!x || !y) return;
    
    const svgX = x - rect.left;
    const svgY = y - rect.top;
    
    // Calculate distance from center
    const dx = svgX - cx;
    const dy = svgY - cy;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // Check if tap is within the pie chart radius
    if (distance > r || distance < r * 0.15) return;
    
    // Calculate angle
    let angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
    if (angle < 0) angle += 360;
    
    const tappedSlice = getSliceAtAngle(angle, slices);
    if (tappedSlice) {
      onSlicePress?.(tappedSlice.label, tappedSlice.value);
    }
  };

  return (
    <View style={{ width: size, height: size }}>
      <Svg
        width={size}
        height={size}
        onPress={handleClick}
        style={{ cursor: 'pointer' }}
      >
        {wedges.map((w, i) => (
          <Path
            key={i}
            d={w.path}
            fill={w.color}
            stroke="#F7F5F0"
            strokeWidth={2}
            opacity={w.opacity}
            onPress={() => onSlicePress?.(w.label, w.value)}
          />
        ))}
      </Svg>
    </View>
  );
}
