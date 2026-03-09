import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Home, Search } from 'lucide-react';

const NotFound = () => (
  <div className="flex min-h-[70vh] items-center justify-center px-4">
    <div className="max-w-md text-center">
      <h1 className="mb-4 text-6xl font-bold text-neutral-900">404</h1>
      <h2 className="mb-4 text-2xl font-semibold text-neutral-900">Page Not Found</h2>
      <p className="mb-8 text-neutral-600">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="flex flex-col justify-center gap-3 sm:flex-row">
        <Button asChild>
          <Link to="/">
            <Home className="mr-2 h-4 w-4" />
            Go Home
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/opportunities">
            <Search className="mr-2 h-4 w-4" />
            Browse Opportunities
          </Link>
        </Button>
      </div>
    </div>
  </div>
);

export default NotFound;
