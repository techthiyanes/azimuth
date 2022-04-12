import { components, paths } from "types/generated/generatedTypes";

export type AzimuthConfig = components["schemas"]["AzimuthConfig"];
export type AvailableDatasetSplits =
  components["schemas"]["AvailableDatasetSplits"];
export type ConfidenceBinDetails =
  components["schemas"]["ConfidenceBinDetails"];
// TODO Fix generated type (problem with python "Array" types)
export type ConfusionMatrixOperation =
  paths["/dataset_splits/{dataset_split_name}/confusion_matrix"]["get"] & {
    responses: {
      200: {
        content: {
          "application/json": ConfusionMatrixResponse;
        };
      };
    };
  };
export type ConfusionMatrixResponse = { confusionMatrix: number[][] };
export type CountPerFilterValue = Partial<OutcomeCountPerFilterValue> &
  UtteranceCountPerFilterValue;
export type DataAction = components["schemas"]["DataAction"];
export type DataActionMapping = components["schemas"]["DataActionMapping"];
export type DataActionResponse = components["schemas"]["DataActionResponse"];
export type DatasetDistributionComparison =
  components["schemas"]["DatasetDistributionComparison"];
export type DatasetDistributionComparisonValue =
  components["schemas"]["DatasetDistributionComparisonValue"];
export type DatasetInfoResponse = components["schemas"]["DatasetInfoResponse"];
export type DatasetSplitName = Exclude<
  components["schemas"]["DatasetSplitName"],
  "all"
>;
export type DatasetWarning = components["schemas"]["DatasetWarning"];
export type DatasetWarningGroup = components["schemas"]["DatasetWarningGroup"];
export type FormatType = components["schemas"]["FormatType"];
export type GetUtterancesResponse =
  components["schemas"]["GetUtterancesResponse"];
export type MetricInfo = components["schemas"]["MetricInfo"];
export type MetricsPerFilterAPIResponse =
  components["schemas"]["MetricsPerFilterAPIResponse"];
export type MetricsPerFilterValue =
  components["schemas"]["MetricsPerFilterValue"];
export type MetricsResponse = components["schemas"]["MetricsAPIResponse"];
export type Outcome = components["schemas"]["OutcomeName"];
export type OutcomeCountPerFilterResponse =
  components["schemas"]["OutcomeCountPerFilterResponse"];
export type OutcomeCountPerFilterValue =
  components["schemas"]["OutcomeCountPerFilterValue"];
export type OutcomeCountPerThreshold =
  components["schemas"]["OutcomeCountPerThresholdValue"];
export type PerturbationTestingSummary =
  components["schemas"]["PerturbationTestingSummary"];
export type PerturbationTestSummary =
  components["schemas"]["PerturbationTestSummary"];
export type PerturbedUtteranceExample =
  components["schemas"]["PerturbedUtteranceExample"];
export type PerturbedUtterance =
  components["schemas"]["PerturbedUtteranceWithClassNames"];
export type PerturbationType = components["schemas"]["PerturbationType"];
export type PlotSpecification = components["schemas"]["PlotSpecification"];
export type PostDataActionRequest =
  components["schemas"]["PostDataActionRequest"];
export type SimilarUtterance = components["schemas"]["SimilarUtterance"];
export type SimilarUtterancesResponse =
  components["schemas"]["SimilarUtterancesResponse"];
export type SmartTag = components["schemas"]["SmartTag"];
export type StatusResponse = components["schemas"]["StatusResponse"];
export type TopWordsResponse = components["schemas"]["TopWordsResponse"];
export type TopWordsResult = components["schemas"]["TopWordsResult"];
export type Utterance = components["schemas"]["Utterance"];
export type UtteranceCountPerFilterResponse =
  components["schemas"]["UtteranceCountPerFilterResponse"];
export type UtteranceCountPerFilterValue =
  components["schemas"]["UtteranceCountPerFilterValue"];
export type UtterancesSortableColumn =
  components["schemas"]["UtterancesSortableColumn"];
export type ValidationError = components["schemas"]["ValidationError"];
