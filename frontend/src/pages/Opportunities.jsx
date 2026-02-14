import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { Bookmark, BookmarkCheck, Building2, Clock, DollarSign, MapPin, Search } from 'lucide-react';

// Mock data
const mockOpportunities = [
  {
    id: "1",
    title: "Senior Software Engineer",
    organization: "TechCorp Inc.",
    type: "Job Offer",
    location: "Remote",
    salary: "$120k - $160k",
    postedDate: "2 days ago",
    deadline: "Mar 15, 2026",
    description: "We're looking for an experienced software engineer to join our platform team...",
    tags: ["React", "Node.js", "TypeScript"],
    saved: false,
  },
  {
    id: "2",
    title: "AI Research Grant",
    organization: "National Science Foundation",
    type: "Funding",
    location: "Nationwide",
    salary: "$500k - $2M",
    postedDate: "1 week ago",
    deadline: "Apr 30, 2026",
    description: "Grant funding for innovative AI research projects in healthcare and education...",
    tags: ["AI/ML", "Research", "Healthcare"],
    saved: true,
  },
  {
    id: "3",
    title: "Mobile App Development Project",
    organization: "HealthTech Solutions",
    type: "Project",
    location: "Hybrid - Boston, MA",
    salary: "$80k - $100k",
    postedDate: "3 days ago",
    deadline: "Mar 25, 2026",
    description: "3-month contract to build a patient management mobile application...",
    tags: ["React Native", "Mobile", "Healthcare"],
    saved: false,
  },
  {
    id: "4",
    title: "Climate Change Research Position",
    organization: "University of California",
    type: "Research",
    location: "Berkeley, CA",
    salary: "$65k - $75k",
    postedDate: "5 days ago",
    deadline: "Apr 10, 2026",
    description: "Postdoctoral position studying climate impact on coastal ecosystems...",
    tags: ["Climate", "Research", "PhD Required"],
    saved: false,
  },
  {
    id: "5",
    title: "UX Designer",
    organization: "DesignHub",
    type: "Job Offer",
    location: "New York, NY",
    salary: "$90k - $120k",
    postedDate: "1 day ago",
    deadline: "Mar 20, 2026",
    description: "Join our design team to create beautiful, user-centered experiences...",
    tags: ["UI/UX", "Figma", "Design Systems"],
    saved: true,
  },
  {
    id: "6",
    title: "Blockchain Development Grant",
    organization: "Ethereum Foundation",
    type: "Funding",
    location: "Remote",
    salary: "$100k - $250k",
    postedDate: "4 days ago",
    deadline: "May 1, 2026",
    description: "Funding for open-source blockchain infrastructure projects...",
    tags: ["Blockchain", "Web3", "Open Source"],
    saved: false,
  },
];

export function OpportunitiesBrowse() {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [savedOpportunities, setSavedOpportunities] = useState(
    new Set(mockOpportunities.filter(o => o.saved).map(o => o.id))
  );

  const toggleSave = (id) => {
    setSavedOpportunities(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const filteredOpportunities = mockOpportunities.filter(opp => {
    const matchesSearch = searchQuery === "" || 
      opp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.organization.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesType = typeFilter === "all" || opp.type === typeFilter;
    
    return matchesSearch && matchesType;
  });

  return (
    <div className="bg-white">
      {/* Search Header */}
      <div className="bg-neutral-50 border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold text-neutral-900 mb-6">Browse Opportunities</h1>
          
          {/* Search Bar */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
              <Input
                type="text"
                placeholder="Search by title, organization, or tags..."
                className="pl-10 h-12"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-[200px] h-12">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="Job Offer">Job Offers</SelectItem>
                <SelectItem value="Project">Projects</SelectItem>
                <SelectItem value="Funding">Funding</SelectItem>
                <SelectItem value="Research">Research</SelectItem>
              </SelectContent>
            </Select>
            <Button className="h-12">
              <Search className="w-5 h-5 mr-2" />
              Search
            </Button>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Filters Sidebar */}
          <aside className="lg:col-span-1">
            <div className="bg-white border border-neutral-200 rounded-lg p-6 sticky top-24">
              <h2 className="font-semibold text-neutral-900 mb-4">Filters</h2>
              
              {/* Location */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-neutral-700 mb-3">Location</h3>
                <div className="space-y-2">
                  {["Remote", "Hybrid", "On-site"].map(location => (
                    <div key={location} className="flex items-center gap-2">
                      <Checkbox id={`location-${location}`} />
                      <label htmlFor={`location-${location}`} className="text-sm text-neutral-600 cursor-pointer">
                        {location}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Salary Range */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-neutral-700 mb-3">Salary Range</h3>
                <div className="space-y-2">
                  {["< $50k", "$50k - $100k", "$100k - $150k", "> $150k"].map(range => (
                    <div key={range} className="flex items-center gap-2">
                      <Checkbox id={`salary-${range}`} />
                      <label htmlFor={`salary-${range}`} className="text-sm text-neutral-600 cursor-pointer">
                        {range}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Posted Date */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-neutral-700 mb-3">Posted</h3>
                <div className="space-y-2">
                  {["Last 24 hours", "Last 7 days", "Last 30 days", "Anytime"].map(date => (
                    <div key={date} className="flex items-center gap-2">
                      <Checkbox id={`date-${date}`} />
                      <label htmlFor={`date-${date}`} className="text-sm text-neutral-600 cursor-pointer">
                        {date}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <Button variant="outline" className="w-full">Clear Filters</Button>
            </div>
          </aside>

          {/* Opportunities List */}
          <div className="lg:col-span-3">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-neutral-600">
                {filteredOpportunities.length} opportunities found
              </p>
              <Select defaultValue="recent">
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="recent">Most Recent</SelectItem>
                  <SelectItem value="deadline">Deadline</SelectItem>
                  <SelectItem value="salary">Salary</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4">
              {filteredOpportunities.map((opportunity) => (
                <div
                  key={opportunity.id}
                  className="bg-white border border-neutral-200 rounded-lg p-6 hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <Link
                          to={`/opportunities/${opportunity.id}`}
                          className="text-xl font-semibold text-neutral-900 hover:text-blue-600"
                        >
                          {opportunity.title}
                        </Link>
                        <Badge variant={opportunity.type === "Job Offer" ? "default" : "secondary"}>
                          {opportunity.type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-neutral-600 mb-3">
                        <span className="flex items-center gap-1">
                          <Building2 className="w-4 h-4" />
                          {opportunity.organization}
                        </span>
                        <span className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          {opportunity.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-4 h-4" />
                          {opportunity.salary}
                        </span>
                      </div>
                      <p className="text-neutral-700 mb-3">{opportunity.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {opportunity.tags.map((tag) => (
                          <Badge key={tag} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => toggleSave(opportunity.id)}
                      className={savedOpportunities.has(opportunity.id) ? "text-blue-600" : ""}
                    >
                      {savedOpportunities.has(opportunity.id) ? (
                        <BookmarkCheck className="w-5 h-5" />
                      ) : (
                        <Bookmark className="w-5 h-5" />
                      )}
                    </Button>
                  </div>
                  <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
                    <div className="flex items-center gap-4 text-sm text-neutral-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        Posted {opportunity.postedDate}
                      </span>
                      <span>Deadline: {opportunity.deadline}</span>
                    </div>
                    <Button asChild>
                      <Link to={`/opportunities/${opportunity.id}`}>View Details</Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
