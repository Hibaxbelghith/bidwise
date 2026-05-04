import { Card, CardContent, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';

const KpiCard = ({ title, value, icon: Icon }) => (
  <Card>
    <CardHeader className="pb-3">
      <CardTitle className="text-sm font-medium text-neutral-600">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="flex items-center justify-between gap-4">
        <p className="text-3xl font-bold text-neutral-900">{value}</p>
        <Icon className="h-8 w-8 text-blue-600" aria-hidden="true" />
      </div>
    </CardContent>
  </Card>
);

export default KpiCard;
