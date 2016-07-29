from urlparse import urljoin
from django.conf import settings
from rest_framework import pagination, serializers

from analytics_data_api.constants import (
    engagement_events,
    enrollment_modes,
    genders,
)
from analytics_data_api.v0 import models


# Below are the enrollment modes supported by this API.
ENROLLMENT_MODES = [enrollment_modes.AUDIT, enrollment_modes.CREDIT, enrollment_modes.HONOR,
                    enrollment_modes.PROFESSIONAL, enrollment_modes.VERIFIED]


class CourseActivityByWeekSerializer(serializers.ModelSerializer):
    """
    Representation of CourseActivityByWeek that excludes the id field.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    activity_type = serializers.SerializerMethodField()

    def get_activity_type(self, obj):
        """
        Lower-case activity type and change active to any.
        """

        activity_type = obj.activity_type.lower()
        if activity_type == 'active':
            activity_type = 'any'

        return activity_type

    class Meta(object):
        model = models.CourseActivityWeekly
        fields = ('interval_start', 'interval_end', 'activity_type', 'count', 'course_id')


class ModelSerializerWithCreatedField(serializers.ModelSerializer):
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)


class ProblemSerializer(serializers.Serializer):
    """
    Serializer for problems.
    """

    module_id = serializers.CharField(required=True)
    total_submissions = serializers.IntegerField(default=0)
    correct_submissions = serializers.IntegerField(default=0)
    part_ids = serializers.CharField()
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)


class ProblemsAndTagsSerializer(serializers.Serializer):
    """
    Serializer for problems and tags.
    """

    module_id = serializers.CharField(required=True)
    total_submissions = serializers.IntegerField(default=0)
    correct_submissions = serializers.IntegerField(default=0)
    tags = serializers.CharField()
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)


class ProblemResponseAnswerDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the Answer Distribution table, without id.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    class Meta(object):
        model = models.ProblemResponseAnswerDistribution
        fields = (
            'course_id',
            'module_id',
            'part_id',
            'correct',
            'count',
            'value_id',
            'answer_value',
            'problem_display_name',
            'question_text',
            'variant',
            'created'
        )


class ConsolidatedAnswerDistributionSerializer(ProblemResponseAnswerDistributionSerializer):
    """
    Serializer for consolidated answer distributions.
    """

    consolidated_variant = serializers.BooleanField()

    class Meta(ProblemResponseAnswerDistributionSerializer.Meta):
        fields = ProblemResponseAnswerDistributionSerializer.Meta.fields + ('consolidated_variant',)

    # pylint: disable=super-on-old-class
    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super(ConsolidatedAnswerDistributionSerializer, self).restore_object(attrs, instance)
        distribution.consolidated_variant = consolidated_variant

        return distribution


class ProblemFirstLastResponseAnswerDistributionSerializer(ProblemResponseAnswerDistributionSerializer):
    """
    Serializer for answer distribution table including counts of first and last response values.
    """

    class Meta(ProblemResponseAnswerDistributionSerializer.Meta):
        model = models.ProblemFirstLastResponseAnswerDistribution
        fields = ProblemResponseAnswerDistributionSerializer.Meta.fields + (
            'first_response_count',
            'last_response_count',
        )

        fields = tuple([field for field in fields if field != 'count'])


class ConsolidatedFirstLastAnswerDistributionSerializer(ProblemFirstLastResponseAnswerDistributionSerializer):
    """
    Serializer for consolidated answer distributions including first attempt counts.
    """

    consolidated_variant = serializers.BooleanField()

    class Meta(ProblemFirstLastResponseAnswerDistributionSerializer.Meta):
        fields = ProblemFirstLastResponseAnswerDistributionSerializer.Meta.fields + ('consolidated_variant',)

    # pylint: disable=super-on-old-class
    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super(ConsolidatedFirstLastAnswerDistributionSerializer, self).restore_object(attrs, instance)
        distribution.consolidated_variant = consolidated_variant

        return distribution


class GradeDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the grade_distribution table without id
    """

    class Meta(object):
        model = models.GradeDistribution
        fields = (
            'module_id',
            'course_id',
            'grade',
            'max_grade',
            'count',
            'created'
        )


class SequentialOpenDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the sequential_open_distribution table without id
    """

    class Meta(object):
        model = models.SequentialOpenDistribution
        fields = (
            'module_id',
            'course_id',
            'count',
            'created'
        )


class DefaultIfNoneMixin(object):

    def default_if_none(self, value, default=0):
        return value if value is not None else default


class BaseCourseEnrollmentModelSerializer(DefaultIfNoneMixin, ModelSerializerWithCreatedField):
    date = serializers.DateField(format=settings.DATE_FORMAT)


class CourseEnrollmentDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment for a single day and course. """

    class Meta(object):
        model = models.CourseEnrollmentDaily
        fields = ('course_id', 'date', 'count', 'created')


class CourseEnrollmentModeDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment, broken down by mode, for a single day and course. """
    audit = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()
    honor = serializers.SerializerMethodField()
    professional = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()

    def get_audit(self, obj):
        return obj.get('audit', 0)

    def get_honor(self, obj):
        return obj.get('honor', 0)

    def get_credit(self, obj):
        return obj.get('credit', 0)

    def get_professional(self, obj):
        return obj.get('professional', 0)

    def get_verified(self, obj):
        return obj.get('verified', 0)

    class Meta(object):
        model = models.CourseEnrollmentModeDaily

        # Declare the dynamically-created fields here as well so that they will be picked up by Swagger.
        fields = ['course_id', 'date', 'count', 'cumulative_count', 'created'] + ENROLLMENT_MODES


class CountrySerializer(serializers.Serializer):
    """
    Serialize country to an object with fields for the complete country name
    and the ISO-3166 two- and three-digit codes.

    Some downstream consumers need two-digit codes, others need three. Both are provided to avoid the need
    for conversion.
    """
    alpha2 = serializers.CharField()
    alpha3 = serializers.CharField()
    name = serializers.CharField()


class CourseEnrollmentByCountrySerializer(BaseCourseEnrollmentModelSerializer):
    # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
    country = CountrySerializer(many=False)

    class Meta(object):
        model = models.CourseEnrollmentByCountry
        fields = ('date', 'course_id', 'country', 'count', 'created')


class CourseEnrollmentByGenderSerializer(BaseCourseEnrollmentModelSerializer):

    female = serializers.IntegerField(default=0)
    male = serializers.IntegerField(default=0)
    other = serializers.IntegerField(default=0)
    unknown = serializers.IntegerField(default=0)

    class Meta(object):
        model = models.CourseEnrollmentByGender
        fields = ('course_id', 'date', 'female', 'male', 'other', 'unknown', 'created')


class CourseEnrollmentByEducationSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByEducation
        fields = ('course_id', 'date', 'education_level', 'count', 'created')


class CourseEnrollmentByBirthYearSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByBirthYear
        fields = ('course_id', 'date', 'birth_year', 'count', 'created')


class CourseActivityWeeklySerializer(serializers.ModelSerializer):
    interval_start = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    interval_end = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    any = serializers.IntegerField(required=False)
    attempted_problem = serializers.IntegerField(required=False)
    played_video = serializers.IntegerField(required=False)
    # posted_forum = serializers.IntegerField(required=False)
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    class Meta(object):
        model = models.CourseActivityWeekly
        # TODO: Add 'posted_forum' here to restore forum data
        fields = ('interval_start', 'interval_end', 'course_id', 'any', 'attempted_problem', 'played_video', 'created')


class VideoSerializer(ModelSerializerWithCreatedField):
    class Meta(object):
        model = models.Video
        fields = (
            'pipeline_video_id',
            'encoded_module_id',
            'duration',
            'segment_length',
            'users_at_start',
            'users_at_end',
            'created'
        )


class VideoTimelineSerializer(ModelSerializerWithCreatedField):
    class Meta(object):
        model = models.VideoTimeline
        fields = (
            'segment',
            'num_users',
            'num_views',
            'created'
        )


class LastUpdatedSerializer(serializers.Serializer):
    last_updated = serializers.DateField(source='date', format=settings.DATE_FORMAT)


class LearnerSerializer(serializers.Serializer, DefaultIfNoneMixin):
    username = serializers.CharField()
    enrollment_mode = serializers.CharField()
    name = serializers.CharField()
    account_url = serializers.SerializerMethodField()
    email = serializers.CharField()
    segments = serializers.ReadOnlyField()
    engagements = serializers.SerializerMethodField()
    enrollment_date = serializers.DateField(format=settings.DATE_FORMAT)
    cohort = serializers.CharField()

    def transform_segments(self, _obj, value):
        # returns null instead of empty strings
        return value or []

    def transform_cohort(self, _obj, value):
        # returns null instead of empty strings
        return value or None

    def get_account_url(self, obj):
        if settings.LMS_USER_ACCOUNT_BASE_URL:
            return urljoin(settings.LMS_USER_ACCOUNT_BASE_URL, obj.username)
        else:
            return None

    def get_engagements(self, obj):
        """
        Add the engagement totals.
        """
        engagements = {}

        # fill in these fields will 0 if values not returned/found
        default_if_none_fields = ['discussion_contributions', 'problems_attempted',
                                  'problems_completed', 'videos_viewed']
        for field in default_if_none_fields:
            engagements[field] = self.default_if_none(getattr(obj, field, None), 0)

        # preserve null values for problem attempts per completed
        engagements['problem_attempts_per_completed'] = getattr(obj, 'problem_attempts_per_completed', None)

        return engagements


class EdxPaginationSerializer(pagination.PageNumberPagination):
    """
    Adds values to the response according to edX REST API Conventions.
    """
    num_pages = serializers.ReadOnlyField(source='paginator.num_pages')


class ElasticsearchDSLSearchSerializer(EdxPaginationSerializer):
    def __init__(self, *args, **kwargs):
        """Make sure that the elasticsearch query is executed."""
        # Because the elasticsearch-dsl search object has a different
        # API from the queryset object that's expected by the django
        # Paginator object, we have to manually execute the query.
        # Note that the `kwargs['instance']` is the Page object, and
        # `kwargs['instance'].object_list` is actually an
        # elasticsearch-dsl search object.
        kwargs['instance'].object_list = kwargs['instance'].object_list.execute()
        super(ElasticsearchDSLSearchSerializer, self).__init__(*args, **kwargs)


class EngagementDaySerializer(DefaultIfNoneMixin, serializers.Serializer):
    date = serializers.DateField(format=settings.DATE_FORMAT)
    problems_attempted = serializers.SerializerMethodField()
    problems_completed = serializers.SerializerMethodField()
    discussion_contributions = serializers.SerializerMethodField()
    videos_viewed = serializers.SerializerMethodField()

    def get_problems_attempted(self, obj):
        return obj.get('problems_attempted', 0)

    def get_problems_completed(self, obj):
        return obj.get('problems_completed', 0)

    def get_discussion_contributions(self, obj):
        return obj.get('discussion_contributions', 0)

    def get_videos_viewed(self, obj):
        return obj.get('videos_viewed', 0)


class DateRangeSerializer(serializers.Serializer):
    start = serializers.DateTimeField(source='start_date', format=settings.DATE_FORMAT)
    end = serializers.DateTimeField(source='end_date', format=settings.DATE_FORMAT)


class EnagementRangeMetricSerializer(serializers.Serializer):
    """
    Serializes ModuleEngagementMetricRanges ('low', 'normal', and 'high') into
    the below_average, average, and above_average ranges represented as arrays.
    If any one of the ranges is not defined, it is not included in the
    serialized output.
    """
    below_average = serializers.SerializerMethodField('get_below_average_range')
    average = serializers.SerializerMethodField('get_average_range')
    above_average = serializers.SerializerMethodField('get_above_average_range')

    def get_average_range(self, obj):
        return self._transform_range(obj['normal_range'])

    def get_below_average_range(self, obj):
        return self._transform_range(obj['low_range'])

    def get_above_average_range(self, obj):
        return self._transform_range(obj['high_range'])

    def _transform_range(self, metric_range):
        return [metric_range.low_value, metric_range.high_value] if metric_range else None


class CourseLearnerMetadataSerializer(serializers.Serializer):
    enrollment_modes = serializers.ReadOnlyField(source='es_data.enrollment_modes')
    segments = serializers.ReadOnlyField(source='es_data.segments')
    cohorts = serializers.ReadOnlyField(source='es_data.cohorts')
    engagement_ranges = serializers.SerializerMethodField()

    def get_engagement_ranges(self, obj):
        query_set = obj['engagement_ranges']
        engagement_ranges = {
            'date_range': DateRangeSerializer(query_set[0] if len(query_set) else None).data
        }

        for metric in engagement_events.EVENTS:
            low_range_queryset = query_set.filter(metric=metric, range_type='low')
            normal_range_queryset = query_set.filter(metric=metric, range_type='normal')
            high_range_queryset = query_set.filter(metric=metric, range_type='high')
            engagement_ranges.update({
                metric: EnagementRangeMetricSerializer({
                    'low_range': low_range_queryset[0] if len(low_range_queryset) else None,
                    'normal_range': normal_range_queryset[0] if len(normal_range_queryset) else None,
                    'high_range': high_range_queryset[0] if len(high_range_queryset) else None,
                }).data
            })

        return engagement_ranges
