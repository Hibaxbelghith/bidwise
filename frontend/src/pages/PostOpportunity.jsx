import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Input } from '../components/ui/input.jsx';
import { Label } from '../components/ui/label.jsx';
import { Textarea } from '../components/ui/textarea.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select.jsx';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card.jsx';
import { ArrowLeft, Save } from 'lucide-react';

const PostOpportunity = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    type: '',
    organization: '',
    location: '',
    locationType: '',
    salary: '',
    employmentType: '',
    experience: '',
    deadline: '',
    description: '',
    responsibilities: '',
    requirements: '',
    benefits: '',
    tags: '',
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    console.log('Form submitted:', formData);
    navigate('/organization/dashboard');
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link
            to="/organization/dashboard"
            className="mb-4 inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </Link>
          <h1 className="mb-2 text-3xl font-bold text-neutral-900">Post New Opportunity</h1>
          <p className="text-neutral-600">Fill in the details to create a new opportunity listing</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Essential details about the opportunity</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="title">Opportunity Title *</Label>
                <Input
                  id="title"
                  placeholder="e.g., Senior Software Engineer"
                  value={formData.title}
                  onChange={(event) => handleChange('title', event.target.value)}
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="type">Type *</Label>
                  <Select value={formData.type} onValueChange={(value) => handleChange('type', value)}>
                    <SelectTrigger id="type">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Job Offer">Job Offer</SelectItem>
                      <SelectItem value="Project">Project</SelectItem>
                      <SelectItem value="Funding">Funding</SelectItem>
                      <SelectItem value="Research">Research</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="organization">Organization Name *</Label>
                  <Input
                    id="organization"
                    placeholder="Your organization"
                    value={formData.organization}
                    onChange={(event) => handleChange('organization', event.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="location">Location *</Label>
                  <Input
                    id="location"
                    placeholder="e.g., San Francisco, CA"
                    value={formData.location}
                    onChange={(event) => handleChange('location', event.target.value)}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="locationType">Location Type *</Label>
                  <Select
                    value={formData.locationType}
                    onValueChange={(value) => handleChange('locationType', value)}
                  >
                    <SelectTrigger id="locationType">
                      <SelectValue placeholder="Select location type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Remote">Remote</SelectItem>
                      <SelectItem value="Hybrid">Hybrid</SelectItem>
                      <SelectItem value="On-site">On-site</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Compensation & Employment Details</CardTitle>
              <CardDescription>Salary, employment type, and experience requirements</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="salary">Salary Range *</Label>
                  <Input
                    id="salary"
                    placeholder="e.g., $80,000 - $120,000"
                    value={formData.salary}
                    onChange={(event) => handleChange('salary', event.target.value)}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="employmentType">Employment Type</Label>
                  <Select
                    value={formData.employmentType}
                    onValueChange={(value) => handleChange('employmentType', value)}
                  >
                    <SelectTrigger id="employmentType">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Full-time">Full-time</SelectItem>
                      <SelectItem value="Part-time">Part-time</SelectItem>
                      <SelectItem value="Contract">Contract</SelectItem>
                      <SelectItem value="Internship">Internship</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="experience">Experience Level</Label>
                  <Select
                    value={formData.experience}
                    onValueChange={(value) => handleChange('experience', value)}
                  >
                    <SelectTrigger id="experience">
                      <SelectValue placeholder="Select level" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Entry Level">Entry Level</SelectItem>
                      <SelectItem value="Mid Level">Mid Level (3-5 years)</SelectItem>
                      <SelectItem value="Senior">Senior (5+ years)</SelectItem>
                      <SelectItem value="Lead">Lead/Principal</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="deadline">Application Deadline *</Label>
                  <Input
                    id="deadline"
                    type="date"
                    value={formData.deadline}
                    onChange={(event) => handleChange('deadline', event.target.value)}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Description & Details</CardTitle>
              <CardDescription>Detailed information about the opportunity</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="description">Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Provide a brief overview of the opportunity..."
                  rows={4}
                  value={formData.description}
                  onChange={(event) => handleChange('description', event.target.value)}
                  required
                />
              </div>

              <div>
                <Label htmlFor="responsibilities">Responsibilities</Label>
                <Textarea
                  id="responsibilities"
                  placeholder="List the main responsibilities (one per line)..."
                  rows={5}
                  value={formData.responsibilities}
                  onChange={(event) => handleChange('responsibilities', event.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="requirements">Requirements</Label>
                <Textarea
                  id="requirements"
                  placeholder="List the requirements and qualifications (one per line)..."
                  rows={5}
                  value={formData.requirements}
                  onChange={(event) => handleChange('requirements', event.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="benefits">Benefits</Label>
                <Textarea
                  id="benefits"
                  placeholder="List the benefits and perks (one per line)..."
                  rows={4}
                  value={formData.benefits}
                  onChange={(event) => handleChange('benefits', event.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="tags">Tags & Skills</Label>
                <Input
                  id="tags"
                  placeholder="e.g., React, Node.js, TypeScript (comma-separated)"
                  value={formData.tags}
                  onChange={(event) => handleChange('tags', event.target.value)}
                />
                <p className="mt-1 text-sm text-neutral-500">
                  Add relevant skills and technologies, separated by commas
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center justify-between gap-4 pt-4">
            <Button type="button" variant="outline" onClick={() => navigate('/organization/dashboard')}>
              Cancel
            </Button>
            <div className="flex gap-3">
              <Button type="button" variant="outline">
                <Save className="mr-2 h-4 w-4" />
                Save Draft
              </Button>
              <Button type="submit">Publish Opportunity</Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PostOpportunity;
