import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Badge } from '../components/ui/badge.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table.jsx';
import { Briefcase, Eye, Plus, TrendingUp, Users } from 'lucide-react';

const postedOpportunities = [
  {
    id: '1',
    title: 'Senior Software Engineer',
    type: 'Job Offer',
    status: 'Active',
    posted: 'Feb 8, 2026',
    deadline: 'Mar 15, 2026',
    applicants: 42,
    views: 328,
  },
  {
    id: '3',
    title: 'Mobile App Development Project',
    type: 'Project',
    status: 'Active',
    posted: 'Feb 7, 2026',
    deadline: 'Mar 25, 2026',
    applicants: 18,
    views: 156,
  },
  {
    id: '9',
    title: 'Junior Developer',
    type: 'Job Offer',
    status: 'Closed',
    posted: 'Jan 15, 2026',
    deadline: 'Feb 15, 2026',
    applicants: 87,
    views: 542,
  },
];

const OrganizationDashboard = () => (
  <div className="min-h-screen bg-neutral-50">
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold text-neutral-900">Organization Dashboard</h1>
          <p className="text-neutral-600">Manage your opportunities and track applications</p>
        </div>
        <Button size="lg" asChild>
          <Link to="/organization/post">
            <Plus className="mr-2 h-5 w-5" />
            Post New Opportunity
          </Link>
        </Button>
      </div>

      <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-neutral-600">Active Opportunities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <p className="text-3xl font-bold text-neutral-900">
                {postedOpportunities.filter((opportunity) => opportunity.status === 'Active').length}
              </p>
              <Briefcase className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-neutral-600">Total Applicants</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <p className="text-3xl font-bold text-neutral-900">
                {postedOpportunities.reduce((sum, opportunity) => sum + opportunity.applicants, 0)}
              </p>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-neutral-600">Total Views</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <p className="text-3xl font-bold text-neutral-900">
                {postedOpportunities.reduce((sum, opportunity) => sum + opportunity.views, 0)}
              </p>
              <Eye className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-neutral-600">Avg. Applicants</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <p className="text-3xl font-bold text-neutral-900">
                {Math.round(
                  postedOpportunities.reduce((sum, opportunity) => sum + opportunity.applicants, 0) /
                    postedOpportunities.length
                )}
              </p>
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Your Opportunities</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline">Filter</Button>
              <Button variant="outline">Export</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Posted</TableHead>
                <TableHead>Deadline</TableHead>
                <TableHead className="text-right">Applicants</TableHead>
                <TableHead className="text-right">Views</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {postedOpportunities.map((opportunity) => (
                <TableRow key={opportunity.id}>
                  <TableCell className="font-medium">
                    <Link to={`/opportunities/${opportunity.id}`} className="hover:text-blue-600">
                      {opportunity.title}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{opportunity.type}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={opportunity.status === 'Active' ? 'default' : 'outline'}>
                      {opportunity.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-neutral-600">{opportunity.posted}</TableCell>
                  <TableCell className="text-neutral-600">{opportunity.deadline}</TableCell>
                  <TableCell className="text-right font-medium">{opportunity.applicants}</TableCell>
                  <TableCell className="text-right text-neutral-600">{opportunity.views}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm">
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm">
                        View
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>API Integration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-neutral-600">
            Integrate BidWise with your existing systems using our API. Automate opportunity posting,
            manage applications, and sync data in real-time.
          </p>
          <div className="flex gap-4">
            <Button variant="outline">View API Docs</Button>
            <Button variant="outline">Generate API Key</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
);

export default OrganizationDashboard;
