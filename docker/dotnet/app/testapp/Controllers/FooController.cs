using System.Linq;
using Microsoft.AspNetCore.Mvc;

namespace TestAppDotnet.Controllers
{
	[Route("/foo")]
	[ApiController]
	public class FooController : ControllerBase
	{
		[HttpGet()]
		public ActionResult<string> Get() => "foo";
	}
}
